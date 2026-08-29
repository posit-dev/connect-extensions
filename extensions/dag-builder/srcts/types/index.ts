/**
 * Type definitions for DAG Builder components
 */

import { EdgeProps } from '@xyflow/react';

export interface ContentNodeData extends Record<string, unknown> {
  label: string;
  contentGuid: string;
  contentType: string;
  contentUrl?: string;
  author?: string;
  description?: string;
  lastDeployed?: string;
}

export interface CustomNodeData extends Record<string, unknown> {
  label: string;
  nodeType: string;
  customType: string;
  description: string;
  icon: string;
  config: Record<string, any>;
}

export interface DAGFlowProps {
  onResetView: () => void;
  onPublishDAG: () => void;
}

export interface ToastMessage {
  id: number;
  message: string;
  type: string;
}

export interface SearchResult {
  guid: string;
  name: string;
  content_type: string;
  url?: string;
  description?: string;
  created_time?: string;
  last_deployed_time?: string;
  author?: string;
}

export interface ArtifactMetadata {
  id: string;
  name: string;
  title: string;
  timestamp: string;
  nodes_count: number;
  edges_count: number;
  batches_count: number;
}

export interface CustomNodeType {
  id: string;
  name: string;
  type: string;
  description: string;
  icon: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface DAGData {
  nodes: any[];
  edges: any[];
  title: string;
}

export interface ActionWithTimestamp {
  artifactId: string;
  timestamp: number;
}

// Re-export commonly used types from ReactFlow
export type { EdgeProps } from '@xyflow/react';
