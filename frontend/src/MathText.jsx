/**
 * MathText — renders a string that may contain LaTeX math delimiters.
 *
 * Supports:
 *   $$...$$ → display (block) math
 *   $...$   → inline math
 *   \(...\) → inline math
 *   \[...\] → display math
 *   Plain text segments are rendered as-is.
 *
 * Uses MathJax (via better-react-mathjax) for robust, high-quality rendering.
 */
import { MathJax } from 'better-react-mathjax';

/**
 * Renders a text string with inline and display LaTeX math via MathJax.
 * MathJax natively handles $...$, $$...$$, \(...\), and \[...\].
 */
export default function MathText({ text, className = '' }) {
  if (!text) return null;

  return (
    <MathJax
      inline
      dynamic
      className={`math-text ${className}`}
    >
      {String(text)}
    </MathJax>
  );
}
