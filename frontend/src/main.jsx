import './globals.js'; // registers window.AppLogger and window.PipelineBus
import React from 'react';
import ReactDOM from 'react-dom/client';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import App from './App.jsx';
import './index.css';

window.katex = katex; // utils.jsx renderMarkdown() calls window.katex.renderToString

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
