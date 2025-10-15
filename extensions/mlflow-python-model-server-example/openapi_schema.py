"""
OpenAPI Schema Generator for MLflow Model API on Posit Connect

This module generates comprehensive OpenAPI documentation for MLflow models deployed
to Posit Connect by:
- Extracting input/output schemas from model metadata
- Creating dynamic examples based on data types
- Generating complete OpenAPI 3.1.0 specifications
- Providing interactive documentation support via /docs and /redoc

The generated schema powers the interactive API documentation available to consumers
of your deployed model on Connect.
"""

import os
import logging

logger = logging.getLogger(__name__)


def extract_model_signature(pyfunc_model):
    """
    Extract input and output schemas from an MLflow model's metadata.
    
    This function analyzes the model's signature to understand:
    - What columns/features the model expects as input
    - The data types of those inputs
    - What the model outputs
    - The data types of outputs
    
    The extracted schema is used to generate helpful examples in the API documentation
    that consumers will see when accessing the deployed API on Connect.
    
    Args:
        pyfunc_model: Loaded MLflow PyFuncModel instance
        
    Returns:
        tuple: A 3-element tuple containing:
            - model_signature_info (str): Human-readable schema description
            - example_input (dict): Sample input data in multiple formats
            - example_output (dict): Sample output data
            
    Example:
        >>> signature, input_ex, output_ex = extract_model_signature(model)
        >>> print(signature)
        **Model Input Schema:**
        ```json
        {
          "feature1": "double",
          "feature2": "double"
        }
        ```
    """
    # Extract schemas from model metadata
    input_schema = pyfunc_model.metadata.get_input_schema()
    output_schema = pyfunc_model.metadata.get_output_schema() if hasattr(
        pyfunc_model.metadata, 'get_output_schema') else None

    model_signature_info = None
    example_input = None
    example_output = None

    # Process input schema if available
    if input_schema:
        try:
            column_names = input_schema.input_names() if hasattr(input_schema, 'input_names') else []
            column_types = input_schema.input_types() if hasattr(input_schema, 'input_types') else []

            if column_names:
                logger.info(f"Extracted model input schema with {len(column_names)} columns")
                logger.info(f"Column names: {column_names}")
                logger.info(f"Column types: {column_types}")

                # Generate realistic example data based on column types
                example_data = []
                example_record = {}

                for i, col_name in enumerate(column_names):
                    # Get type-appropriate example value
                    if i < len(column_types):
                        col_type = str(column_types[i])
                        example_value = _generate_example_value(col_type)
                    else:
                        # Default to float if type unknown
                        example_value = 1.0

                    example_record[col_name] = example_value
                    example_data.append(example_value)

                # Create examples in formats that MLflow accepts
                # Convert column names to strings to handle integer column names
                example_input = {
                    'dataframe_split': {
                        'columns': [str(name) for name in column_names],
                        'data': [example_data]
                    },
                    'dataframe_records': [example_record],
                    'column_names': [str(name) for name in column_names],
                    'column_types': [str(t) for t in column_types] if column_types else []
                }

                # Format schema as human-readable JSON
                model_signature_info = _format_schema_as_json("Input", column_names, column_types)
                
        except Exception as e:
            logger.warning(f"Could not extract input schema: {e}")
    else:
        logger.info("Model has no input schema defined")

    # Process output schema if available
    if output_schema:
        try:
            output_names = output_schema.input_names() if hasattr(output_schema, 'input_names') else []
            output_types = output_schema.input_types() if hasattr(output_schema, 'input_types') else []

            if output_names:
                logger.info(f"Extracted model output schema with {len(output_names)} outputs")

                # Generate example predictions
                example_predictions = []
                for i, col_name in enumerate(output_names):
                    if i < len(output_types):
                        col_type = str(output_types[i])
                        example_value = _generate_example_value(col_type, is_output=True)
                    else:
                        example_value = 0.95  # Default prediction value

                    example_predictions.append(example_value)

                example_output = {
                    'predictions': example_predictions
                }

                # Append output schema to documentation
                output_schema_info = _format_schema_as_json("Output", output_names, output_types)
                if model_signature_info:
                    model_signature_info += f"\n\n{output_schema_info}"
                else:
                    model_signature_info = output_schema_info

        except Exception as e:
            logger.warning(f"Could not extract output schema: {e}")
    else:
        logger.info("Model has no output schema defined")

    return model_signature_info, example_input, example_output


def _generate_example_value(col_type, is_output=False):
    """
    Generate an appropriate example value based on the column's data type.
    
    Args:
        col_type (str): The data type (e.g., "int64", "float", "string")
        is_output (bool): Whether this is for output (affects default values)
        
    Returns:
        Appropriate example value for the data type
    """
    col_type_lower = col_type.lower()

    # Integer types
    if 'int' in col_type_lower or 'long' in col_type_lower:
        return 0 if is_output else 1
    
    # Floating point types
    elif 'float' in col_type_lower or 'double' in col_type_lower:
        return 0.95 if is_output else 1.0
    
    # Boolean types
    elif 'bool' in col_type_lower:
        return True
    
    # String types
    elif 'string' in col_type_lower or 'str' in col_type_lower:
        return "prediction" if is_output else "example"
    
    # Default to float
    else:
        return 0.95 if is_output else 1.0


def _format_schema_as_json(schema_type, names, types):
    """
    Format a schema as a JSON code block for documentation.
    
    Args:
        schema_type (str): "Input" or "Output"
        names (list): Column/field names
        types (list): Corresponding data types
        
    Returns:
        str: Formatted JSON schema string
    """
    schema_lines = [f"**Model {schema_type} Schema:**", "```json", "{"]

    for i, name in enumerate(names):
        # Clean up type names (remove "DataType." prefix)
        col_type = str(types[i]).replace('DataType.', '') if i < len(types) else 'any'
        # Add comma except for last item
        comma = "," if i < len(names) - 1 else ""
        schema_lines.append(f'  "{name}": "{col_type}"{comma}')

    schema_lines.append("}")
    schema_lines.append("```")

    return "\n".join(schema_lines)


def configure_openapi_metadata(app, model_uri, tracking_uri, model_signature_info=None):
    """
    Configure OpenAPI metadata for the FastAPI application deployed on Posit Connect.
    
    This adds essential information to the API documentation including:
    - Title and version
    - Model URI and tracking server information
    - Input/output schema descriptions
    - Connect-specific authentication details
    
    Args:
        app: FastAPI application instance
        model_uri (str): The MLflow model URI
        tracking_uri (str): The MLflow tracking server URI
        model_signature_info (str, optional): Formatted model schema information
    """
    # Set basic API metadata
    app.title = "MLflow Model Serving API"
    app.version = "1.0.0"
    
    # Build the correct API base URL for Connect
    connect_server = os.getenv('CONNECT_SERVER', '')
    content_guid = os.getenv('CONNECT_CONTENT_GUID', '')
    
    if connect_server and content_guid:
        # When deployed to Connect, use the full content URL
        api_base_url = f"{connect_server}content/{content_guid}"
    else:
        # For local development
        api_base_url = "http://localhost:8000"
    
    app.contact = {
        "name": "MLflow Model API",
        "url": tracking_uri,
    }

    # Include model schema in description if available
    schema_section = ""
    if model_signature_info:
        schema_section = f"\n\n{model_signature_info}\n"

    # Build comprehensive API description with Connect-specific information
    app.description = f"""
## MLflow Model Serving API on Posit Connect

Serve machine learning models deployed through MLflow's PyFunc flavor with a RESTful API on Posit Connect.

### Features

* **Health Monitoring**: Check service health and availability
* **Version Information**: Get MLflow version details
* **Real-time Predictions**: Make predictions using your deployed model
* **Multiple Input Formats**: Support for JSON, CSV, and TensorFlow formats
* **Interactive Documentation**: This Swagger UI interface for testing

### Model Information

* **Model URI**: `{model_uri}`
* **MLflow Tracking Server**: `{tracking_uri}`
* **API Base URL**: `{api_base_url}`
{schema_section}
### Supported Input Formats

The `/invocations` endpoint accepts several formats:

1. **JSON (dataframe_split)**: Pandas DataFrame in split-orient format
2. **JSON (dataframe_records)**: Pandas DataFrame in records-orient format
3. **JSON (instances)**: TensorFlow Serving compatible format
4. **JSON (inputs)**: Alternative TensorFlow format
5. **CSV**: Standard comma-separated values

### Authentication on Posit Connect

**This API is deployed on Posit Connect:**
- Authentication is handled by Connect's content access controls
- The API uses the publisher's Connect API key to access MLflow automatically
- No additional authentication headers required when accessing through Connect
- Access is controlled via Connect's content settings

### Response Format

Predictions return JSON with a `predictions` array containing model outputs.
    """

    # Define endpoint categories for better organization
    app.openapi_tags = [
        {
            "name": "health",
            "description": "Health check and monitoring endpoints"
        },
        {
            "name": "model",
            "description": "Model prediction and inference endpoints"
        },
        {
            "name": "info",
            "description": "Service information and metadata endpoints"
        }
    ]


def generate_openapi_schema(app, model_uri, tracking_uri, model_signature_info=None,
                           example_input=None, example_output=None):
    """
    Generate a complete OpenAPI 3.1.0 schema for the MLflow Model API.
    
    This creates a comprehensive API specification that includes:
    - All standard MLflow endpoints
    - Model-specific schemas and examples
    - Input format documentation
    - Response format specifications
    - Proper server URLs for Connect deployment
    
    The schema is used by FastAPI to power /docs and /redoc endpoints.
    
    Args:
        app: FastAPI application instance
        model_uri (str): The MLflow model URI
        tracking_uri (str): The MLflow tracking server URI
        model_signature_info (str, optional): Model schema description
        example_input (dict, optional): Sample input data
        example_output (dict, optional): Sample output data
        
    Returns:
        function: A function that returns the OpenAPI schema dictionary
    """

    def custom_openapi():
        """Generate the OpenAPI schema on demand."""
        # Return cached schema if available
        if app.openapi_schema:
            return app.openapi_schema

        # Build the correct server URL for Connect
        connect_server = os.getenv('CONNECT_SERVER', '')
        content_guid = os.getenv('CONNECT_CONTENT_GUID', '')
        
        servers = []
        if connect_server and content_guid:
            # When deployed to Connect, use the full content URL
            servers.append({
                "url": f"{connect_server}content/{content_guid}",
                "description": "Posit Connect Deployment"
            })
        else:
            # For local development
            servers.append({
                "url": "http://localhost:8000",
                "description": "Local Development Server"
            })

        # Build complete OpenAPI 3.1.0 specification
        openapi_schema = {
            "openapi": "3.1.0",
            "info": {
                "title": app.title,
                "version": app.version,
                "description": app.description,
                "contact": app.contact
            },
            "servers": servers,
            "tags": app.openapi_tags,
            "paths": _generate_paths(model_signature_info, example_input, example_output)
        }

        # Cache the schema
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return custom_openapi


def _generate_paths(model_signature_info, example_input, example_output):
    """
    Generate the paths section of the OpenAPI schema.
    
    Creates specifications for all API endpoints with proper request/response schemas.
    """
    return {
        "/ping": _generate_ping_path(),
        "/health": _generate_health_path(),
        "/version": _generate_version_path(),
        "/invocations": _generate_invocations_path(model_signature_info, example_input, example_output)
    }


def _generate_ping_path():
    """Generate OpenAPI specification for the /ping health check endpoint."""
    return {
        "get": {
            "tags": ["health"],
            "summary": "Health Check (Ping)",
            "description": "Quick health check that returns immediately if the service is running. Returns a newline character if healthy, 404 if the model failed to load.",
            "operationId": "ping",
            "responses": {
                "200": {
                    "description": "Service is healthy",
                    "content": {
                        "application/json": {
                            "schema": {"type": "string"},
                            "example": "\n"
                        }
                    }
                },
                "404": {
                    "description": "Service unhealthy - model could not be loaded"
                }
            }
        }
    }


def _generate_health_path():
    """Generate OpenAPI specification for the /health endpoint."""
    return {
        "get": {
            "tags": ["health"],
            "summary": "Detailed Health Check",
            "description": "Comprehensive health check for the model service. Returns HTTP 200 if healthy, 404 if unhealthy.",
            "operationId": "health",
            "responses": {
                "200": {
                    "description": "Service is healthy and ready to serve predictions",
                    "content": {
                        "application/json": {
                            "schema": {"type": "string"},
                            "example": "\n"
                        }
                    }
                },
                "404": {
                    "description": "Service unhealthy - model is not available"
                }
            }
        }
    }


def _generate_version_path():
    """Generate OpenAPI specification for the /version endpoint."""
    return {
        "get": {
            "tags": ["info"],
            "summary": "Get MLflow Version",
            "description": "Returns the version of MLflow running this service. Useful for debugging and compatibility checks.",
            "operationId": "version",
            "responses": {
                "200": {
                    "description": "MLflow version string",
                    "content": {
                        "application/json": {
                            "schema": {"type": "string"},
                            "example": "2.9.2"
                        }
                    }
                }
            }
        }
    }


def _generate_invocations_path(model_signature_info, example_input, example_output):
    """
    Generate OpenAPI specification for the /invocations prediction endpoint.
    
    Includes model-specific examples and schemas when available.
    """
    # Build comprehensive description with examples
    description = f"""Make predictions using the deployed MLflow model.

{model_signature_info if model_signature_info else ''}

**Input Format Examples:**

1. **JSON with dataframe_split:**
```json
{{
  "dataframe_split": {{
    "columns": ["feature1", "feature2"],
    "data": [[1.0, 2.0], [3.0, 4.0]]
  }}
}}
```

2. **JSON with dataframe_records:**
```json
{{
  "dataframe_records": [
    {{"feature1": 1.0, "feature2": 2.0}},
    {{"feature1": 3.0, "feature2": 4.0}}
  ]
}}
```

3. **CSV format:**
```
feature1,feature2
1.0,2.0
3.0,4.0
```

**Response Format:**
```json
{{
  "predictions": [result1, result2, ...]
}}
```"""

    # Prepare default examples (used when no model schema available)
    default_split = {
        "columns": ["feature1", "feature2"],
        "data": [[1.0, 2.0], [3.0, 4.0]]
    }
    default_records = [
        {"feature1": 1.0, "feature2": 2.0},
        {"feature1": 3.0, "feature2": 4.0}
    ]
    default_csv = "feature1,feature2\n1.0,2.0\n3.0,4.0"
    default_output = {"predictions": [0.95, 0.87]}

    # Use model-based examples when available
    split_example = example_input['dataframe_split'] if example_input else default_split
    records_example = example_input['dataframe_records'] if example_input else default_records
    
    # Generate CSV example from model schema
    if example_input:
        # Convert all column names to strings and ensure data values are also strings for CSV
        csv_example = (
            ','.join(str(name) for name in example_input['column_names']) + '\n' +
            ','.join(str(v) for v in example_input['dataframe_split']['data'][0])
        )
    else:
        csv_example = default_csv
        
    output_example = example_output if example_output else default_output

    # Build complete endpoint specification
    return {
        "post": {
            "tags": ["model"],
            "summary": "Make Predictions",
            "description": description,
            "operationId": "invocations",
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object"
                        },
                        "examples": {
                            "dataframe_split": {
                                "summary": "DataFrame Split Format" + (" (Model Schema)" if example_input else ""),
                                "value": {
                                    "dataframe_split": split_example
                                }
                            },
                            "dataframe_records": {
                                "summary": "DataFrame Records Format" + (" (Model Schema)" if example_input else ""),
                                "value": {
                                    "dataframe_records": records_example
                                }
                            }
                        }
                    },
                    "text/csv": {
                        "schema": {
                            "type": "string"
                        },
                        "example": csv_example
                    }
                },
                "required": True
            },
            "responses": {
                "200": {
                    "description": "Successful prediction" + (" (based on model schema)" if example_output else ""),
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "predictions": {
                                        "type": "array",
                                        "description": "Array of prediction results"
                                    }
                                }
                            },
                            "example": output_example
                        }
                    }
                },
                "400": {
                    "description": "Bad request - invalid input format or missing required fields"
                },
                "415": {
                    "description": "Unsupported media type - use application/json or text/csv"
                },
                "500": {
                    "description": "Server error during prediction"
                }
            }
        }
    }
