import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  ReactFlowProvider,
  useReactFlow,
  ConnectionMode,
  getIncomers,
  getOutgoers,
  getConnectedEdges,
  IsValidConnection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useWebSocket } from './hooks/useWebSocket';

// Import our refactored components and types
import { nodeTypes } from './components/nodes';
import { edgeTypes } from './components/edges';
import { NotificationComponent } from './components/notifications';
import {
  ContentNodeData,
  CustomNodeData,
  DAGFlowProps,
  ToastMessage,
  SearchResult,
  ArtifactMetadata,
  CustomNodeType,
  ValidationResult,
  ActionWithTimestamp
} from './types';

// REST API Helper Functions
async function apiRequest(url: string, options: RequestInit = {}) {
  const response = await fetch(`${window.location.href}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

async function saveDAG(nodes: Node[], edges: Edge[], title: string, loadedDagId: string | null) {
  return apiRequest('api/dags/save', {
    method: 'POST',
    body: JSON.stringify({ nodes, edges, title, loaded_dag_id: loadedDagId }),
  });
}

async function loadDAG(artifactId: string) {
  return apiRequest(`api/dags/${artifactId}`, { method: 'GET' });
}

async function deleteDAG(artifactId: string) {
  return apiRequest(`api/dags/${artifactId}`, { method: 'DELETE' });
}

async function publishDAG(nodes: Node[], edges: Edge[], title: string) {
  return apiRequest('api/dags/publish', {
    method: 'POST',
    body: JSON.stringify({ nodes, edges, title }),
  });
}

async function publishSavedDAG(artifactId: string) {
  return apiRequest(`api/dags/${artifactId}/publish`, { method: 'POST' });
}

async function cloneDAG(artifactId: string) {
  return apiRequest(`api/dags/${artifactId}/clone`, { method: 'POST' });
}

// Helper to show local toast messages (bypassing WebSocket)
function showLocalToast(message: string, type: 'info' | 'success' | 'warning' | 'error') {
  // Dispatch a custom event that NotificationComponent can listen to
  window.dispatchEvent(new CustomEvent('localToast', {
    detail: { message, type }
  }));
}

interface DAGFlowExtendedProps extends DAGFlowProps {
  onLoadDAGRequest?: (loadHandler: (artifactId: string) => Promise<void>) => void;
  onUserGuidChange?: (guid: string | null) => void;
  onLoadedDagIdChange?: (dagId: string | null) => void;
}

function DAGFlow({ onResetView, onPublishDAG, onLoadDAGRequest, onUserGuidChange, onLoadedDagIdChange }: DAGFlowExtendedProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const { fitView, getNodes, getEdges, screenToFlowPosition } = useReactFlow();
  const { isConnected, sendMessage, onMessage, offMessage } = useWebSocket();

  // Local state
  const [dagTitle, setDagTitle] = useState<string>('');
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [loadedDagId, setLoadedDagId] = useState<string | null>(null);
  const [userGuid, setUserGuid] = useState<string | null>(null);

  // Handler for loading DAG that can be called from outside
  const handleLoadDAGFromArtifact = useCallback(async (artifactId: string) => {
    try {
      const result = await loadDAG(artifactId);
      setNodes(result.dag.nodes || []);
      setEdges(result.dag.edges || []);
      setDagTitle(result.dag.title || '');
      setLoadedDagId(result.artifact_id);
      showLocalToast(`Loaded DAG: ${result.dag.title}`, 'success');
      setTimeout(() => fitView(), 100);
    } catch (error) {
      console.error('Failed to load DAG:', error);
      throw error; // Re-throw so caller can handle
    }
  }, [setNodes, setEdges, fitView]);

  // Expose load handler to parent
  useEffect(() => {
    if (onLoadDAGRequest) {
      onLoadDAGRequest(handleLoadDAGFromArtifact);
    }
  }, [handleLoadDAGFromArtifact, onLoadDAGRequest]);

  // Notify parent of userGuid changes
  useEffect(() => {
    if (onUserGuidChange) {
      onUserGuidChange(userGuid);
    }
  }, [userGuid, onUserGuidChange]);

  // Notify parent of loadedDagId changes
  useEffect(() => {
    if (onLoadedDagIdChange) {
      onLoadedDagIdChange(loadedDagId);
    }
  }, [loadedDagId, onLoadedDagIdChange]);

  // Set up WebSocket message handlers
  // Only for real-time updates: validation results and user GUID
  useEffect(() => {
    const handleValidation = (data: ValidationResult) => {
      setValidationResult(data);
    };

    const handleUserGuid = (data: { guid: string }) => {
      setUserGuid(data.guid);
    };

    const handleLoadedDagId = (data: { id: string }) => {
      // Backend may still broadcast this after save operations
      setLoadedDagId(data.id);
    };

    onMessage('dag_validation', handleValidation);
    onMessage('user_guid', handleUserGuid);
    onMessage('loaded_dag_id', handleLoadedDagId);

    return () => {
      offMessage('dag_validation', handleValidation);
      offMessage('user_guid', handleUserGuid);
      offMessage('loaded_dag_id', handleLoadedDagId);
    };
  }, [onMessage, offMessage]);

  // Send DAG data updates to backend for validation
  useEffect(() => {
    if (isConnected && nodes.length > 0) {
      sendMessage('dag_data', { nodes, edges, title: dagTitle });
    }
  }, [nodes, edges, dagTitle, isConnected, sendMessage]);

  // Cycle prevention logic
  const isValidConnection: IsValidConnection = useCallback(
    (connection) => {
      const nodes = getNodes();
      const edges = getEdges();
      const target = nodes.find((node) => node.id === connection.target);

      if (!target) return false;
      if (target.id === connection.source) return false;

      const hasCycle = (node: Node, visited = new Set<string>()) => {
        if (visited.has(node.id)) return false;
        visited.add(node.id);

        for (const outgoer of getOutgoers(node, nodes, edges)) {
          if (outgoer.id === connection.source) return true;
          if (hasCycle(outgoer, visited)) return true;
        }

        return false;
      };

      return !hasCycle(target);
    },
    [getNodes, getEdges],
  );

  const onConnect = useCallback(
    (params: Connection) => {
      console.log('Connecting nodes:', params);
      const newEdge = { ...params, type: 'deletable' };
      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges]
  );

  const onNodesDelete = useCallback(
    (deleted: Node[]) => {
      let remainingNodes = [...nodes];
      setEdges(
        deleted.reduce((acc, node) => {
          const incomers = getIncomers(node, remainingNodes, acc);
          const outgoers = getOutgoers(node, remainingNodes, acc);
          const connectedEdges = getConnectedEdges([node], acc);

          const remainingEdges = acc.filter((edge) => !connectedEdges.includes(edge));

          const createdEdges = incomers.flatMap(({ id: source }) =>
            outgoers.map(({ id: target }) => ({
              id: `${source}->${target}`,
              source,
              target,
              type: 'deletable',
            })),
          );

          remainingNodes = remainingNodes.filter((rn) => rn.id !== node.id);

          return [...remainingEdges, ...createdEdges];
        }, edges),
      );
    },
    [nodes, edges, setEdges],
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      const nodeDataString = event.dataTransfer.getData('application/nodedata');

      if (!type || !nodeDataString) {
        return;
      }

      const nodeData = JSON.parse(nodeDataString);

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Node = {
        id: `node-${Date.now()}`,
        type,
        position,
        data: nodeData,
      };

      console.log('Dropping node at position:', position);
      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes, screenToFlowPosition]
  );

  const handleResetView = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setDagTitle('');
    setLoadedDagId(null);
    setTimeout(() => fitView(), 100);
  }, [setNodes, setEdges, fitView]);

  const handlePublishDAG = useCallback(async () => {
    console.log('Publishing DAG triggered at:', Date.now());
    try {
      await publishDAG(nodes, edges, dagTitle);
      // Status updates will come via WebSocket
    } catch (error) {
      console.error('Failed to publish DAG:', error);
      showLocalToast(`Failed to publish: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    }
  }, [nodes, edges, dagTitle]);

  const isSaveDisabled = useMemo(() => {
    return !validationResult?.isValid || nodes.length === 0 || !dagTitle.trim();
  }, [validationResult, nodes.length, dagTitle]);

  const handleSaveDAG = useCallback(async () => {
    console.log('Saving DAG triggered at:', Date.now());
    try {
      const result = await saveDAG(nodes, edges, dagTitle, loadedDagId);
      setLoadedDagId(result.artifact_id);
      showLocalToast(result.message, 'success');
    } catch (error) {
      console.error('Failed to save DAG:', error);
      showLocalToast(`Failed to save: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    }
  }, [nodes, edges, dagTitle, loadedDagId]);

  return (
    <div className="dag-container">
      <div className="dag-toolbar">
        <div className="dag-title-section">
          <label htmlFor="dag-title" className="title-label">DAG Title:</label>
          <input
            id="dag-title"
            type="text"
            value={dagTitle}
            onChange={(e) => setDagTitle(e.target.value)}
            placeholder="Enter DAG title... (required to save)"
            className="title-input"
          />
        </div>
        <div className="toolbar-actions">
          <button onClick={handleResetView} className="toolbar-button">
            Reset View
          </button>
          <button
            onClick={handleSaveDAG}
            className={`toolbar-button ${isSaveDisabled ? 'disabled' : 'publish'}`}
            disabled={isSaveDisabled}
          >
            Save DAG
          </button>
        </div>
        {validationResult && !validationResult.isValid && (
          <div className="validation-errors">
            <strong>Validation Errors:</strong>
            <ul>
              {validationResult.errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <div className="dag-flow">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodesDelete={onNodesDelete}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          isValidConnection={isValidConnection}
          fitView
          connectionMode={ConnectionMode.Strict}
          snapToGrid={true}
          snapGrid={[15, 15]}
          connectionRadius={10}
          defaultEdgeOptions={{
            style: { strokeWidth: 2, stroke: '#666' },
            type: 'deletable',
          }}
          elevateEdgesOnSelect={true}
          selectNodesOnDrag={false}
        >
          <Controls />
          <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        </ReactFlow>
      </div>
    </div>
  );
}

function ContentSidebar() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const { isConnected, sendMessage, onMessage, offMessage } = useWebSocket();

  // Set up message handlers
  useEffect(() => {
    const handleSearchResults = (data: SearchResult[]) => {
      console.log('Search results received:', data);
      setSearchResults(data);
    };

    onMessage('search_results', handleSearchResults);

    return () => {
      offMessage('search_results', handleSearchResults);
    };
  }, [onMessage, offMessage]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery.trim().length >= 2 && isConnected) {
        console.log('Triggering search for:', searchQuery.trim());
        sendMessage('search_query', { query: searchQuery.trim() });
      } else if (searchQuery.trim().length === 0 && isConnected) {
        sendMessage('search_query', { query: '' });
        setSearchResults([]);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery, isConnected, sendMessage]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim().length >= 2) {
      sendMessage('search_query', { query: searchQuery.trim() });
    }
  };

  const onDragStart = (event: React.DragEvent, nodeData: any) => {
    event.dataTransfer.setData('application/reactflow', 'contentNode');
    event.dataTransfer.setData('application/nodedata', JSON.stringify({
      label: nodeData.name,
      contentGuid: nodeData.guid,
      contentType: nodeData.content_type,
      contentUrl: nodeData.url || '',
      description: nodeData.description || '',
      author: nodeData.author || 'Unknown',
      lastDeployed: nodeData.last_deployed_time || nodeData.created_time || ''
    }));
    event.dataTransfer.effectAllowed = 'move';
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return 'Unknown';
    }
  };

  return (
    <div className="content-sidebar">
      <div className="sidebar-header">
        <h2>Content Library</h2>
      </div>
      <div className="sidebar-search">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search content..."
            className="search-input"
          />
        </form>
      </div>
      <div className="sidebar-content">
        <div className="search-results">
          {searchQuery.trim().length < 2 ? (
            <div className="search-hint">
              Enter at least 2 characters to search for content
            </div>
          ) : searchResults && searchResults.length > 0 ? (
            searchResults.map((item) => (
              <div
                key={item.guid}
                className="search-result-item draggable"
                draggable
                onDragStart={(event) => onDragStart(event, item)}
              >
                <div className="result-name">{item.name}</div>
                <div className="result-meta">
                  <div className="result-type">{item.content_type}</div>
                  <div className="result-author">By: {item.author || 'Unknown'}</div>
                  <div className="result-date">Updated: {formatDate(item.last_deployed_time || item.created_time || '')}</div>
                </div>
                {item.description && (
                  <div className="result-description">{item.description}</div>
                )}
                <div className="result-guid">{item.guid}</div>
                <div className="drag-hint">Drag to canvas</div>
              </div>
            ))
          ) : (
            <div className="no-results">
              No content found for "{searchQuery}"
            </div>
          )}
        </div>
        <CustomNodesPane />
      </div>
    </div>
  );
}

function CustomNodesPane() {
  const customNodes = [
    {
      id: 'webhook',
      name: 'Webhook',
      type: 'webhook',
      description: 'Make HTTP API calls',
      icon: '🔗'
    },
    {
      id: 'delay',
      name: 'Delay',
      type: 'delay',
      description: 'Add time delay between operations',
      icon: '⏱️'
    },
    {
      id: 'condition',
      name: 'Condition',
      type: 'condition',
      description: 'Conditional logic branching',
      icon: '🔀'
    }
  ];

  const onDragStart = (event: React.DragEvent, nodeData: any) => {
    event.dataTransfer.setData('application/reactflow', 'customNode');
    event.dataTransfer.setData('application/nodedata', JSON.stringify({
      label: nodeData.name,
      nodeType: nodeData.type,
      customType: nodeData.type,
      description: nodeData.description,
      icon: nodeData.icon,
      config: getDefaultConfig(nodeData.type)
    }));
    event.dataTransfer.effectAllowed = 'move';
  };

  const getDefaultConfig = (nodeType: string) => {
    switch (nodeType) {
      case 'webhook':
        return {
          url: '',
          method: 'GET',
          headers: '{}',
          body: ''
        };
      case 'delay':
        return {
          duration: 5,
          unit: 'seconds'
        };
      case 'condition':
        return {
          condition: '',
          conditionType: 'custom',
          trueAction: 'continue',
          falseAction: 'skip',
          targetNodeId: '',
          notificationMessage: ''
        };
      default:
        return {};
    }
  };

  return (
    <div className="custom-nodes-pane">
      <div className="custom-nodes-header">
        <h3>Custom Actions</h3>
      </div>
      <div className="custom-nodes-list">
        {customNodes.map((node) => (
          <div
            key={node.id}
            className="custom-node-item draggable"
            draggable
            onDragStart={(event) => onDragStart(event, node)}
          >
            <div className="custom-node-icon">{node.icon}</div>
            <div className="custom-node-content">
              <div className="custom-node-name">{node.name}</div>
              <div className="custom-node-description">{node.description}</div>
            </div>
            <div className="drag-hint">Drag to canvas</div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface ArtifactsSidebarProps {
  userGuid: string | null;
  onLoadDAG: (artifactId: string) => Promise<void>;
  loadedDagId: string | null;
}

function ArtifactsSidebar({ userGuid, onLoadDAG, loadedDagId }: ArtifactsSidebarProps) {
  const [artifactsList, setArtifactsList] = useState<ArtifactMetadata[]>([]);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{artifactId: string, artifactName: string} | null>(null);
  const [publishingArtifacts, setPublishingArtifacts] = useState<Set<string>>(new Set());
  const { isConnected, sendMessage, onMessage, offMessage } = useWebSocket();

  // Set up message handlers
  useEffect(() => {
    const handleArtifactsList = (data: ArtifactMetadata[]) => {
      setArtifactsList(data);
    };

    const handleLogEvent = (msg: { message: string; type: string }) => {
      // Clear publishing state when we receive success/error messages about publishing
      if (msg.message.includes('published successfully') || msg.message.includes('Publishing failed')) {
        // Extract artifact info from message and clear publishing state
        // For now, clear all publishing states when any publish completes
        setPublishingArtifacts(new Set());
      }
    };

    // WebSocket handler for artifacts list updates (broadcast from backend after save/delete)
    onMessage('artifacts_list', handleArtifactsList);
    onMessage('logEvent', handleLogEvent);

    return () => {
      offMessage('artifacts_list', handleArtifactsList);
      offMessage('logEvent', handleLogEvent);
    };
  }, [onMessage, offMessage]);

  const handleCardClick = async (artifactId: string) => {
    console.log('Card clicked for artifact:', artifactId);
    try {
      await onLoadDAG(artifactId);
    } catch (error) {
      console.error('Failed to load DAG:', error);
      showLocalToast(`Failed to load: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    }
  };

  const handleDownload = (e: React.MouseEvent, artifactId: string) => {
    e.stopPropagation(); // Prevent card click
    console.log('Download clicked for artifact:', artifactId);
    if (!userGuid) {
      showLocalToast('User not authenticated', 'error');
      return;
    }
    // Download via direct endpoint
    window.location.href = `${window.location.href}download-artifact/${userGuid}/${artifactId}`;
  };

  const handlePublishDirect = async (e: React.MouseEvent, artifactId: string) => {
    e.stopPropagation(); // Prevent card click
    console.log('Publish direct clicked for artifact:', artifactId);

    // Mark as publishing
    setPublishingArtifacts(prev => new Set(prev).add(artifactId));

    try {
      await publishSavedDAG(artifactId);
      // Status updates will come via WebSocket
      // Publishing state will be cleared when we receive completion message
    } catch (error) {
      console.error('Failed to publish DAG:', error);
      showLocalToast(`Failed to publish: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      // Clear publishing state on error
      setPublishingArtifacts(prev => {
        const next = new Set(prev);
        next.delete(artifactId);
        return next;
      });
    }
  };

  const handleCloneClick = async (e: React.MouseEvent, artifactId: string) => {
    e.stopPropagation(); // Prevent card click
    console.log('Clone clicked for artifact:', artifactId);
    try {
      const result = await cloneDAG(artifactId);
      showLocalToast(result.message, 'success');
    } catch (error) {
      console.error('Failed to clone DAG:', error);
      showLocalToast(`Failed to clone: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    }
  };

  const handleDeleteClick = (e: React.MouseEvent, artifactId: string, artifactName: string) => {
    e.stopPropagation(); // Prevent card click
    setDeleteConfirmation({ artifactId, artifactName });
  };

  const handleDeleteConfirm = async () => {
    if (deleteConfirmation) {
      console.log('Delete confirmed for artifact:', deleteConfirmation.artifactId);
      try {
        const result = await deleteDAG(deleteConfirmation.artifactId);
        showLocalToast(result.message, 'success');
        setDeleteConfirmation(null);
      } catch (error) {
        console.error('Failed to delete DAG:', error);
        showLocalToast(`Failed to delete: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
        setDeleteConfirmation(null);
      }
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmation(null);
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return 'Unknown';
    }
  };

  return (
    <div className="artifacts-sidebar">
      <div className="sidebar-header">
        <h2>Saved DAGs</h2>
      </div>
      <div className="sidebar-content">
        <div className="artifacts-list">
          {artifactsList && artifactsList.length > 0 ? (
            artifactsList.map((artifact) => (
              <div
                key={artifact.id}
                className={`artifact-item ${artifact.id === loadedDagId ? 'artifact-item-active' : ''}`}
                onClick={() => handleCardClick(artifact.id)}
                style={{ cursor: 'pointer' }}
              >
                <div className="artifact-header">
                  <div className="artifact-name">
                    {publishingArtifacts.has(artifact.id) && (
                      <span className="publishing-spinner">⟳</span>
                    )}
                    {artifact.title || artifact.name}
                    {artifact.id === loadedDagId && <span className="loaded-indicator"> ● Loaded</span>}
                  </div>
                  <button
                    className="delete-artifact-button"
                    onClick={(e) => handleDeleteClick(e, artifact.id, artifact.title || artifact.name)}
                    title="Delete DAG"
                  >
                    ×
                  </button>
                </div>
                <div className="artifact-meta">
                  <div>Published: {formatDate(artifact.timestamp)}</div>
                </div>
                <div className="artifact-stats">
                  <div className="artifact-stat">{artifact.nodes_count} nodes</div>
                  <div className="artifact-stat">{artifact.edges_count} edges</div>
                  <div className="artifact-stat">{artifact.batches_count} batches</div>
                </div>
                <div className="artifact-id">{artifact.id}</div>
                <div className="artifact-buttons">
                  <button
                    className="clone-button"
                    onClick={(e) => handleCloneClick(e, artifact.id)}
                    title="Clone this DAG"
                  >
                    Clone
                  </button>
                  <button
                    className="download-button"
                    onClick={(e) => handleDownload(e, artifact.id)}
                  >
                    Download
                  </button>
                  <button
                    className="publish-direct-button"
                    onClick={(e) => handlePublishDirect(e, artifact.id)}
                    disabled={publishingArtifacts.has(artifact.id)}
                  >
                    {publishingArtifacts.has(artifact.id) ? 'Publishing...' : 'Publish'}
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="no-artifacts">
              No saved DAGs yet. Save a DAG to see it here.
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirmation && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Delete DAG</h3>
            </div>
            <div className="modal-body">
              <p>Are you sure you want to delete the DAG "{deleteConfirmation.artifactName}"?</p>
              <p>This action cannot be undone.</p>
            </div>
            <div className="modal-footer">
              <button className="modal-button cancel" onClick={handleDeleteCancel}>
                Cancel
              </button>
              <button className="modal-button delete" onClick={handleDeleteConfirm}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DAGBuilder() {
  const [loadDAGHandler, setLoadDAGHandler] = useState<((artifactId: string) => Promise<void>) | null>(null);
  const [userGuid, setUserGuid] = useState<string | null>(null);
  const [loadedDagId, setLoadedDagId] = useState<string | null>(null);

  const handleResetView = () => {
    // Reset functionality handled in DAGFlow component
  };

  const handlePublishDAG = () => {
    // Publish functionality handled in DAGFlow component
  };

  const handleLoadDAGRequest = useCallback((handler: (artifactId: string) => Promise<void>) => {
    setLoadDAGHandler(() => handler);
  }, []);

  const handleUserGuidChange = useCallback((guid: string | null) => {
    setUserGuid(guid);
  }, []);

  const handleLoadedDagIdChange = useCallback((dagId: string | null) => {
    setLoadedDagId(dagId);
  }, []);

  return (
    <ReactFlowProvider>
      <div className="dag-builder">
        <ContentSidebar />
        <DAGFlow
          onResetView={handleResetView}
          onPublishDAG={handlePublishDAG}
          onLoadDAGRequest={handleLoadDAGRequest}
          onUserGuidChange={handleUserGuidChange}
          onLoadedDagIdChange={handleLoadedDagIdChange}
        />
        <ArtifactsSidebar
          userGuid={userGuid}
          onLoadDAG={loadDAGHandler || (async () => { throw new Error('Load handler not ready'); })}
          loadedDagId={loadedDagId}
        />
        <NotificationComponent />
      </div>
    </ReactFlowProvider>
  );
}
