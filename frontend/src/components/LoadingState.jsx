export default function LoadingState({ message = 'Loading…' }) {
  return (
    <div className="state-loading">
      <div className="spinner" />
      <p>{message}</p>
    </div>
  );
}
