import { ContentNode } from './ContentNode';
import { CustomNode } from './CustomNode';

// Re-export components
export { ContentNode } from './ContentNode';
export { CustomNode } from './CustomNode';

// Node type registry for ReactFlow
export const nodeTypes = {
  contentNode: ContentNode,
  customNode: CustomNode,
};