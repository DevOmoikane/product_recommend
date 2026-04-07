const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = 'ws://localhost:8000';

export const executeWorkflow = async (workflowData) => {
  const response = await fetch(`${API_BASE_URL}/api/workflow/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(workflowData),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const stopWorkflow = async (executionId) => {
  const response = await fetch(`${API_BASE_URL}/api/workflow/stop/${executionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 404) {
      // just remove the ws connection and consider it stopped
      return { success: true };
    }
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const connectToExecution = (executionId, onMessage, onError, onClose) => {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/workflow/${executionId}`);

  ws.onopen = () => {
    console.log('WebSocket connected for execution:', executionId);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.(error);
  };

  ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
    onClose?.(event);
  };

  return ws;
};