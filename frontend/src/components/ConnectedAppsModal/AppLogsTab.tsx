import React, { useState } from 'react'
import type { AppActivityLog } from '../../types/account'
import { AppLogo } from './AppLogos'

interface AppLogsTabProps {
  logs: AppActivityLog[]
  onClearLogs: () => Promise<void>
}

export const AppLogsTab: React.FC<AppLogsTabProps> = ({ logs, onClearLogs }) => {
  const [selectedAppFilter, setSelectedAppFilter] = useState<string>('all')
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null)

  const filteredLogs = logs.filter((log) => {
    if (selectedAppFilter !== 'all' && log.app_id !== selectedAppFilter) return false
    if (selectedTypeFilter !== 'all' && log.event_type !== selectedTypeFilter) return false
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchesMsg = log.message.toLowerCase().includes(q)
      const matchesUser = log.user_email.toLowerCase().includes(q)
      const matchesApp = log.app_name.toLowerCase().includes(q)
      if (!matchesMsg && !matchesUser && !matchesApp) return false
    }
    return true
  })

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(filteredLogs, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute('href', dataStr)
    downloadAnchor.setAttribute('download', `xeren_app_logs_${Date.now()}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  return (
    <div className="app-logs-container" data-testid="app-logs-tab-content">
      <div className="logs-header-bar">
        <div>
          <h4>App Activity & Session Log</h4>
          <p>Real-time audit log of authentications, sync cycles, and tool runs under user accounts.</p>
        </div>
        <div className="logs-actions-right">
          <button
            type="button"
            className="export-logs-btn"
            onClick={handleExportJson}
            data-testid="export-logs-btn"
          >
            Export JSON
          </button>
          <button
            type="button"
            className="clear-logs-btn"
            onClick={onClearLogs}
            data-testid="clear-logs-btn"
          >
            Clear Log
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="logs-filter-toolbar">
        <div className="filter-group">
          <label htmlFor="filter-app-select">Filter App:</label>
          <select
            id="filter-app-select"
            value={selectedAppFilter}
            onChange={(e) => setSelectedAppFilter(e.target.value)}
            className="logs-select"
            data-testid="filter-app-select"
          >
            <option value="all">All Apps & AIs</option>
            <option value="gemini">Google Gemini</option>
            <option value="canva">Canva Design</option>
            <option value="huggingface">Hugging Face</option>
            <option value="openai">OpenAI / ChatGPT</option>
            <option value="claude">Anthropic Claude</option>
            <option value="perplexity">Perplexity AI</option>
            <option value="midjourney">Midjourney AI</option>
            <option value="github">GitHub</option>
            <option value="supabase">Supabase</option>
            <option value="notion">Notion</option>
            <option value="gdrive">Google Drive & Workspace</option>
            <option value="slack">Slack</option>
            <option value="discord">Discord</option>
            <option value="spotify">Spotify</option>
            <option value="linear">Linear</option>
            <option value="figma">Figma</option>
            <option value="filesystem">Local Filesystem</option>
            <option value="sqlite">SQLite Database</option>
            <option value="system">Xeren Security Vault</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-type-select">Event Type:</label>
          <select
            id="filter-type-select"
            value={selectedTypeFilter}
            onChange={(e) => setSelectedTypeFilter(e.target.value)}
            className="logs-select"
            data-testid="filter-type-select"
          >
            <option value="all">All Events</option>
            <option value="auth">AUTH (Login / Logout)</option>
            <option value="sync">SYNC (Account Verification)</option>
            <option value="tool_call">TOOL CALL (Action Run)</option>
            <option value="error">ERROR (Failures)</option>
          </select>
        </div>

        <div className="search-filter-box">
          <input
            type="text"
            placeholder="Search log messages or user emails..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="logs-search-input"
            data-testid="logs-search-input"
          />
        </div>
      </div>

      {/* Log Entries List */}
      <div className="log-entries-list" data-testid="log-entries-list">
        {filteredLogs.length === 0 ? (
          <div className="empty-logs-state">
            <span>No activity logs matched your current filters.</span>
          </div>
        ) : (
          filteredLogs.map((entry) => {
            const isExpanded = expandedLogId === entry.log_id
            const hasDetails = entry.details && Object.keys(entry.details).length > 0
            return (
              <div
                key={entry.log_id}
                className={`log-entry-row type-${entry.event_type}`}
                data-testid={`log-entry-${entry.log_id}`}
              >
                <div className="log-main-line">
                  <span className="log-timestamp">{entry.timestamp}</span>
                  <span className="log-app-badge">
                    <AppLogo appId={entry.app_id} size={15} className="log-app-logo" />
                    <span>{entry.app_name}</span>
                  </span>
                  <span className={`log-event-tag tag-${entry.event_type}`}>
                    {entry.event_type.toUpperCase()}
                  </span>
                  <span className="log-user-tag">
                    <code>{entry.user_email}</code>
                  </span>
                  <span className="log-message-text">{entry.message}</span>
                  {hasDetails && (
                    <button
                      type="button"
                      className="expand-log-btn"
                      onClick={() => setExpandedLogId(isExpanded ? null : entry.log_id)}
                    >
                      {isExpanded ? 'Hide ▲' : 'Details ▼'}
                    </button>
                  )}
                </div>

                {isExpanded && hasDetails && (
                  <div className="log-expanded-payload">
                    <pre><code>{JSON.stringify(entry.details, null, 2)}</code></pre>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
