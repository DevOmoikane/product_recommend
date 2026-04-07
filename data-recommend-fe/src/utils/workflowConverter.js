export const convertToBackendFormat = (nodes, edges, workflowName = 'workflow', description = '') => {
  const nodeMap = {};
  nodes.forEach(node => {
    const nodeDefinition = node.data.nodeDefinition;
    nodeMap[node.id] = {
      definition: nodeDefinition,
      type: nodeDefinition?.full_class_path || node.type,
      inputs: nodeDefinition?.inputs?.map(i => i.id) || [],
      outputs: nodeDefinition?.outputs?.map(o => o.id) || [],
      function: nodeDefinition?.outputs?.[0]?.function || 'output',
    };
  });

  const workflowNodes = nodes.map((node) => {
    const fields = {};
    const nodeDefinition = node.data.nodeDefinition;
    
    if (nodeDefinition && nodeDefinition.fields) {
      nodeDefinition.fields.forEach((field) => {
        // the React Flow library has the edge connections inverted, the source is the target and the target is the source
        const connectedEdge = edges.find(e => e.source === node.id && e.sourceHandle === field.name);
        if (!connectedEdge) {
          const value = node.data.config?.[field.name];
          if (value !== undefined && value !== '') {
            fields[field.name] = value;
          }
        }
      });
    }

    nodeDefinition?.inputs?.forEach(input => {
      const connectedEdge = edges.find(e => e.source === node.id && e.sourceHandle === input.id);
      if (connectedEdge) {
        fields[input.id] = connectedEdge.source;
      }
    });

    const processingFunction = nodeMap[node.id]?.function || 'output';
    const type = nodeDefinition?.full_class_path || node.type;

    return {
      id: node.id,
      type,
      fields,
      processing_function: processingFunction,
    };
  });

  const connections = edges.map((edge) => {
    let from_node, from_output, to_node, to_input;

    from_node = edge.target;
    from_output = edge.targetHandle;
    to_node = edge.source;
    to_input = edge.sourceHandle;

    return {
      from_node,
      from_output,
      to_node,
      to_input,
    };
  });

  return {
    workflow: {
      name: workflowName,
      description,
      nodes: workflowNodes,
      connections,
    },
    initial_data: {},
  };
};