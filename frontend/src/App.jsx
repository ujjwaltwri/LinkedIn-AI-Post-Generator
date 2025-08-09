import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState(null); // State to store user info

  // This effect runs once when the component loads
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const userId = params.get('user_id');
    const userName = params.get('name');

    if (userId && userName) {
      // If user info is in the URL, save it to state
      setUser({ id: userId, name: userName });
      // Clean the URL
      window.history.replaceState({}, document.title, "/");
    }
  }, []);
  
  const BACKEND_URL = 'https://influence-os-project.onrender.com';

  const handleLogin = () => {
    window.location.href = `${BACKEND_URL}/login/linkedin`;
  };

  const handleCreatePost = async (e) => {
    e.preventDefault();
    if (!user) {
      setMessage('Please log in first.');
      return;
    }
    setIsLoading(true);
    setMessage('');

    try {
      const response = await fetch(`${BACKEND_URL}/posts/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          prompt: prompt,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'An error occurred.');
      }

      setMessage('Post successfully published to LinkedIn!');
      setPrompt('');
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Influence OS AI Agent</h1>
        {user ? (
          <p>Welcome, {user.name}!</p>
        ) : (
          <p>Automate your LinkedIn Personal Branding</p>
        )}
      </header>

      <main className="App-main">
        {user ? (
          <>
            <h2>Create a New Post</h2>
            <form onSubmit={handleCreatePost}>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter a simple prompt for your post..."
                required
                disabled={isLoading}
              />
              <button type="submit" disabled={isLoading}>
                {isLoading ? 'Generating & Posting...' : 'Generate and Post'}
              </button>
            </form>
          </>
        ) : (
          <button onClick={handleLogin} className="login-button">
            Login with LinkedIn
          </button>
        )}
        {message && <p className="message">{message}</p>}
      </main>
    </div>
  );
}

export default App;