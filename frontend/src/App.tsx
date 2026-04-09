import React from 'react';

export default function App() {
  return (
    <div style={{ 
      background: '#1f2937', 
      padding: '2rem', 
      margin: '2rem 0',
      borderRadius: '12px',
      border: '2px solid #10b981'
    }}>
      <h2 style={{ color: '#10b981', margin: '0 0 1rem 0' }}>
        ✅ React is Mounted and Working!
      </h2>
      <p style={{ color: '#f9fafb', margin: '0' }}>
        If you can see this green box, React has successfully rendered.
      </p>
      <p style={{ color: '#9ca3af', marginTop: '1rem' }}>
        React {React.version} • TypeScript • Vite
      </p>
    </div>
  );
}
