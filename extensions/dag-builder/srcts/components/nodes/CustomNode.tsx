import React from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import { CustomNodeData } from '../../types';

interface CustomNodeProps {
  data: CustomNodeData;
  id: string;
}

export function CustomNode({ data, id }: CustomNodeProps) {
  const [config, setConfig] = React.useState(data.config || {});
  const [isExpanded, setIsExpanded] = React.useState(false);

  // Update the node data when config changes
  const { setNodes } = useReactFlow();

  React.useEffect(() => {
    setNodes((nodes) =>
      nodes.map((node) =>
        node.id === id
          ? {
              ...node,
              data: {
                ...node.data,
                config: config
              }
            }
          : node
      )
    );
  }, [config, id, setNodes]);

  const updateConfig = (key: string, value: any) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const renderForm = () => {
    switch (data.customType) {
      case 'webhook':
        return (
          <div className="custom-node-form">
            <div className="form-group">
              <label>URL:</label>
              <input
                type="text"
                value={config.url || ''}
                onChange={(e) => updateConfig('url', e.target.value)}
                placeholder="https://api.example.com/endpoint"
                className="form-input"
              />
            </div>
            <div className="form-group">
              <label>Method:</label>
              <select
                value={config.method || 'GET'}
                onChange={(e) => updateConfig('method', e.target.value)}
                className="form-select"
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="PATCH">PATCH</option>
                <option value="DELETE">DELETE</option>
              </select>
            </div>
            <div className="form-group">
              <label>Headers (JSON):</label>
              <textarea
                value={config.headers || '{}'}
                onChange={(e) => updateConfig('headers', e.target.value)}
                placeholder='{"Content-Type": "application/json"}'
                className="form-textarea"
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Body (JSON):</label>
              <textarea
                value={config.body || ''}
                onChange={(e) => updateConfig('body', e.target.value)}
                placeholder='{"key": "value"}'
                className="form-textarea"
                rows={4}
              />
            </div>
          </div>
        );
      case 'delay':
        return (
          <div className="custom-node-form">
            <div className="form-group">
              <label>Duration:</label>
              <input
                type="number"
                value={config.duration || 5}
                onChange={(e) => updateConfig('duration', parseInt(e.target.value))}
                className="form-input"
                min="1"
              />
            </div>
            <div className="form-group">
              <label>Unit:</label>
              <select
                value={config.unit || 'seconds'}
                onChange={(e) => updateConfig('unit', e.target.value)}
                className="form-select"
              >
                <option value="seconds">Seconds</option>
                <option value="minutes">Minutes</option>
                <option value="hours">Hours</option>
              </select>
            </div>
          </div>
        );
      case 'condition':
        const conditionExamples: Record<string, string> = {
          'time_business_hours': 'runtime_context["current_hour"] >= 9 and runtime_context["current_hour"] <= 17',
          'time_weekday': 'runtime_context["is_weekday"]',
          'time_friday': 'runtime_context["weekday"] == 4',
          'previous_success': 'previous_nodes.get("node_id", {}).get("status") == "success"',
          'previous_http_ok': 'previous_nodes.get("node_id", {}).get("status_code") == 200',
          'previous_has_data': 'len(previous_nodes.get("node_id", {}).get("data", [])) > 0',
          'environment_prod': 'runtime_context["environment"] == "production"',
          'file_exists': 'runtime_context["file_exists"]("/path/to/file")',
          'custom': ''
        };

        return (
          <div className="custom-node-form">
            <div className="form-group">
              <label>Condition Type:</label>
              <select
                value={config.conditionType || 'custom'}
                onChange={(e) => {
                  const type = e.target.value;
                  updateConfig('conditionType', type);
                  if (type !== 'custom') {
                    updateConfig('condition', conditionExamples[type]);
                  }
                }}
                className="form-select"
              >
                <option value="custom">Custom Expression</option>
                <optgroup label="Time-based">
                  <option value="time_business_hours">Business Hours (9-5)</option>
                  <option value="time_weekday">Weekday Only</option>
                  <option value="time_friday">Friday Only</option>
                </optgroup>
                <optgroup label="Previous Node Results">
                  <option value="previous_success">Previous Node Succeeded</option>
                  <option value="previous_http_ok">Previous HTTP 200 OK</option>
                  <option value="previous_has_data">Previous Node Has Data</option>
                </optgroup>
                <optgroup label="Environment">
                  <option value="environment_prod">Production Environment</option>
                  <option value="file_exists">File Exists</option>
                </optgroup>
              </select>
            </div>
            <div className="form-group">
              <label>Condition Expression:</label>
              <textarea
                value={config.condition || ''}
                onChange={(e) => updateConfig('condition', e.target.value)}
                placeholder='Available: previous_nodes, runtime_context'
                className="form-textarea condition-textarea"
                rows={3}
              />
              <div className="condition-help">
                <details>
                  <summary>Available Variables</summary>
                  <div className="help-content">
                    <strong>previous_nodes:</strong> Dict of all previous node results<br/>
                    <strong>runtime_context:</strong> Current time, environment, utilities<br/>
                    <strong>Examples:</strong><br/>
                    • <code>previous_nodes["node-123"]["status"] == "success"</code><br/>
                    • <code>runtime_context["current_hour"] &lt; 12</code><br/>
                    • <code>len(previous_nodes["data-node"]["rows"]) &gt; 100</code>
                  </div>
                </details>
              </div>
            </div>
            <div className="form-group">
              <label>If True:</label>
              <select
                value={config.trueAction || 'continue'}
                onChange={(e) => updateConfig('trueAction', e.target.value)}
                className="form-select"
              >
                <option value="continue">Continue Execution</option>
                <option value="skip_remaining">Skip Remaining Batches</option>
                <option value="stop">Stop All Execution</option>
                <option value="notify">Send Notification</option>
                <option value="retry_previous">Retry Previous Step</option>
              </select>
            </div>
            <div className="form-group">
              <label>If False:</label>
              <select
                value={config.falseAction || 'skip_remaining'}
                onChange={(e) => updateConfig('falseAction', e.target.value)}
                className="form-select"
              >
                <option value="continue">Continue Execution</option>
                <option value="skip_remaining">Skip Remaining Batches</option>
                <option value="stop">Stop All Execution</option>
                <option value="notify">Send Notification</option>
                <option value="retry_previous">Retry Previous Step</option>
              </select>
            </div>
            {(config.trueAction === 'notify' || config.falseAction === 'notify') && (
              <div className="form-group">
                <label>Notification Message:</label>
                <input
                  type="text"
                  value={config.notificationMessage || ''}
                  onChange={(e) => updateConfig('notificationMessage', e.target.value)}
                  placeholder="Alert: Condition triggered"
                  className="form-input"
                />
              </div>
            )}
          </div>
        );
      default:
        return <div>No configuration available</div>;
    }
  };

  return (
    <div className="custom-node">
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          background: '#ff6b6b',
          border: '2px solid #fff',
          width: 12,
          height: 12,
        }}
        isConnectable={true}
      />
      <div className="node-header">
        <div className="custom-node-title">
          <span className="custom-node-icon">{data.icon}</span>
          <strong>{data.label}</strong>
        </div>
        <button
          className="expand-button"
          onClick={() => setIsExpanded(!isExpanded)}
          title={isExpanded ? "Collapse" : "Expand"}
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>
      {isExpanded && (
        <div className="node-body">
          {renderForm()}
        </div>
      )}
      {!isExpanded && (
        <div className="node-summary">
          <div className="custom-node-description">{data.description}</div>
        </div>
      )}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{
          background: '#ff6b6b',
          border: '2px solid #fff',
          width: 12,
          height: 12,
        }}
        isConnectable={true}
      />
    </div>
  );
}