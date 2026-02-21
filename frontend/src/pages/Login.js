import React, { useState } from 'react';
import api from '../services/api';
import './Login.css';

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await api.post('/auth/login', { username, password });
      const { access_token, user } = response.data;
      onLogin(access_token, user);
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page" data-testid="login-page">
      <div className="login-container">
        <div className="login-header">
          <div className="login-logo">H</div>
          <h1>HOOREN ERP</h1>
          <p>Food Products Management System</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              type="text"
              className="form-control"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
              autoFocus
              data-testid="login-username"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-control"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              data-testid="login-password"
            />
          </div>

          {error && <div className="login-error" data-testid="login-error">{error}</div>}

          <button 
            type="submit" 
            className="btn btn-primary login-btn"
            disabled={loading}
            data-testid="login-submit"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="login-footer">
          <p>HOOREN FOOD PRODUCTS</p>
          <p>Survey No 409, Ranuj, Patan, Gujarat</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
