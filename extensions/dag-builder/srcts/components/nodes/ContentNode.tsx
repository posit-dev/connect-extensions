import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { ContentNodeData } from '../../types';

interface ContentNodeProps {
  data: ContentNodeData;
}

export function ContentNode({ data }: ContentNodeProps) {
  return (
    <div className="content-node">
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          background: '#28a745',
          border: '2px solid #fff',
          width: 12,
          height: 12,
        }}
        isConnectable={true}
      />
      <div className="node-header">
        <strong>{data.label}</strong>
      </div>
      <div className="node-body">
        <div className="content-type">{data.contentType}</div>
        <div className="content-author">By: {data.author || 'Unknown'}</div>
        <div className="content-guid">{data.contentGuid}</div>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{
          background: '#007bff',
          border: '2px solid #fff',
          width: 12,
          height: 12,
        }}
        isConnectable={true}
      />
    </div>
  );
}