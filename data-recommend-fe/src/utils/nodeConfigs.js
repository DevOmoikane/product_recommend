export const NODE_TYPES = {
  DATA_SOURCE: 'dataSource',
  SQL_QUERY: 'sqlQuery',
  ML_MODEL: 'mlModel',
  PROCESSOR: 'processor',
  OUTPUT: 'output',
};

export const DATA_TYPES = {
  RAW_DATA: 'rawData',
  PROCESSED_DATA: 'processedData',
  MODEL: 'model',
  PREDICTIONS: 'predictions',
};

export const DATA_TYPE_CONFIG = {
  [DATA_TYPES.RAW_DATA]: { label: 'Raw Data', color: '#4CAF50' },
  [DATA_TYPES.PROCESSED_DATA]: { label: 'Processed Data', color: '#2196F3' },
  [DATA_TYPES.MODEL]: { label: 'Model', color: '#9C27B0' },
  [DATA_TYPES.PREDICTIONS]: { label: 'Predictions', color: '#FF9800' },
};

export const NODE_CONFIG = {
  [NODE_TYPES.DATA_SOURCE]: {
    label: 'Data Source',
    icon: '📥',
    color: '#4CAF50',
    description: 'Import data from various sources',
    inputs: [],
    outputs: [{ id: 'output', label: 'Data', type: DATA_TYPES.RAW_DATA, color: '#4CAF50' }],
    fields: [
      { name: 'sourceType', label: 'Source Type', type: 'select', options: ['csv', 'api', 'database'] },
      { name: 'connectionString', label: 'Connection String', type: 'text' },
    ],
  },
  [NODE_TYPES.SQL_QUERY]: {
    label: 'SQL Query',
    icon: '🔍',
    color: '#2196F3',
    description: 'Execute SQL queries on data',
    inputs: [{ id: 'input', label: 'Data', type: DATA_TYPES.RAW_DATA, color: '#4CAF50', connectionCount: 2 }],
    outputs: [{ id: 'output', label: 'Result', type: DATA_TYPES.PROCESSED_DATA, color: '#2196F3' }],
    fields: [
      { name: 'query', label: 'SQL Query', type: 'textarea' },
      { name: 'database', label: 'Database', type: 'text' },
    ],
  },
  [NODE_TYPES.ML_MODEL]: {
    label: 'ML Model',
    icon: '🤖',
    color: '#9C27B0',
    description: 'Configure ML model parameters',
    inputs: [{ id: 'input', label: 'Training Data', type: DATA_TYPES.PROCESSED_DATA, color: '#2196F3' }],
    outputs: [
      { id: 'model', label: 'Model', type: DATA_TYPES.MODEL, color: '#9C27B0' },
      { id: 'predictions', label: 'Predictions', type: DATA_TYPES.PREDICTIONS, color: '#FF9800' },
    ],
    fields: [
      { name: 'modelType', label: 'Model Type', type: 'select', options: ['regression', 'classification', 'clustering'] },
      { name: 'parameters', label: 'Parameters (JSON)', type: 'textarea' },
      { name: 'apiEndpoint', label: 'API Endpoint', type: 'text' },
    ],
  },
  [NODE_TYPES.PROCESSOR]: {
    label: 'Processor',
    icon: '⚙️',
    color: '#FF9800',
    description: 'Transform and process data',
    inputs: [
      { id: 'input1', label: 'Input 1', type: DATA_TYPES.RAW_DATA, color: '#4CAF50' },
      { id: 'input2', label: 'Input 2', type: DATA_TYPES.PROCESSED_DATA, color: '#2196F3' },
    ],
    outputs: [{ id: 'output', label: 'Processed', type: DATA_TYPES.PROCESSED_DATA, color: '#2196F3' }],
    fields: [
      { name: 'operation', label: 'Operation', type: 'select', options: ['filter', 'aggregate', 'transform', 'join'] },
      { name: 'config', label: 'Configuration (JSON)', type: 'textarea' },
    ],
  },
  [NODE_TYPES.OUTPUT]: {
    label: 'Output',
    icon: '📤',
    color: '#F44336',
    description: 'Export processed data',
    inputs: [
      { id: 'input1', label: 'Raw Data', type: DATA_TYPES.RAW_DATA, color: '#4CAF50' },
      { id: 'input2', label: 'Processed', type: DATA_TYPES.PROCESSED_DATA, color: '#2196F3' },
      { id: 'input3', label: 'Predictions', type: DATA_TYPES.PREDICTIONS, color: '#FF9800' },
    ],
    outputs: [],
    fields: [
      { name: 'outputType', label: 'Output Type', type: 'select', options: ['csv', 'json', 'api'] },
      { name: 'destination', label: 'Destination', type: 'text' },
    ],
  },
};

export const COMPATIBLE_CONNECTIONS = {
  [DATA_TYPES.RAW_DATA]: [DATA_TYPES.RAW_DATA, DATA_TYPES.PROCESSED_DATA],
  [DATA_TYPES.PROCESSED_DATA]: [DATA_TYPES.PROCESSED_DATA, DATA_TYPES.MODEL, DATA_TYPES.PREDICTIONS],
  [DATA_TYPES.MODEL]: [],
  [DATA_TYPES.PREDICTIONS]: [],
};

export const createNode = (type, position) => {
  const config = NODE_CONFIG[type];
  const defaultData = {
    label: config.label,
    config: {},
    isValid: false,
  };
  
  config.fields.forEach(field => {
    if (field.type === 'select' && field.options) {
      defaultData.config[field.name] = field.options[0];
    } else {
      defaultData.config[field.name] = '';
    }
  });

  return {
    id: `${type}-${Date.now()}`,
    type,
    position,
    data: defaultData,
  };
};

export const validateNode = (node) => {
  const config = NODE_CONFIG[node.type];
  if (!config) return { isValid: false, errors: ['Unknown node type'] };

  const errors = [];
  config.fields.forEach(field => {
    const value = node.data.config[field.name];
    if (!value || (typeof value === 'string' && value.trim() === '')) {
      errors.push(`${field.label} is required`);
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
  };
};
