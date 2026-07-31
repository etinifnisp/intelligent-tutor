export default function ErrorState({ message, onRetry }) {
  return (
    <div className="state-error">
      <p>{message || 'Something went wrong.'}</p>
      {onRetry && (
        <button className="btn btn-secondary" onClick={onRetry}>Try again</button>
      )}
    </div>
  );
}
