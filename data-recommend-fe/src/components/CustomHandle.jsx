import { React } from 'react';
import { Handle } from '@xyflow/react';
 
const CustomHandle = (props) => {
  return (
    <Handle
      {...props}
      style={{
        background: 'none',
        border: 'none',
        width: '1em',
        height: '1em',
      }}
    >
      {props.position === 'right' && props.label && (
        <span style={{
          position: 'absolute',
          top: '50%',
          right: '100%',
          textAlign: 'right',
          fontSize: '0.4em',
          transform: 'translateY(-50%)',
          whiteSpace: 'nowrap',
          color: props.style?.background || props.style?.borderColor || '#FFFFFF',
        }}>
          {props.label}
        </span>
      )}
      <div style={{
        width: '0.6em',
        height: '0.6em',
        borderRadius: '50%',
        background: props.style?.background || props.style?.borderColor || '#FFFFFF',
        backgroundColor: props.style.background,
        border: `2px solid ${props.style.borderColor}`,
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
      }}
      />
      {props.position === 'left' && props.label && (
        <span style={{
          position: 'absolute',
          top: '50%',
          left: '100%',
          textAlign: 'left',
          fontSize: '0.4em',
          transform: 'translateY(-50%)',
          whiteSpace: 'nowrap',
          color: props.style?.background || props.style?.borderColor || '#FFFFFF',
        }}>
          {props.label}
        </span>
      )}
    </Handle>
  );
};
 
export default CustomHandle;