import BaseNode from './BaseNode';

export default function SqlQueryNode(props) {
  return <BaseNode {...props} type="sqlQuery" />;
}