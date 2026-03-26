import { React } from 'react';
import { Handle, useNodeConnections } from '@xyflow/react';
 
const CustomHandle = (props) => {
  const connections = useNodeConnections({
    handleType: props.type,
  });
 
  return (
    <Handle
      {...props}
      isConnectable={props.type==="source" || connections.length < props.connectionCount }
    />
  );
};
 
export default CustomHandle;