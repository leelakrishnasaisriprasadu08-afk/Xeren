import React from 'react'
import './NotificationsDrawer.css'

export interface SystemNotification {
  id: string
  timestamp: string
  title: string
  message: string
  type: 'security' | 'order' | 'research' | 'system' | 'project_invite'
  read: boolean
  inviteId?: string
  projectId?: string
  projectName?: string
  inviterHandle?: string
  role?: string
}

interface NotificationsDrawerProps {
  isOpen: boolean
  onClose: () => void
  notifications: SystemNotification[]
  onClearAll: () => void
  onMarkAllRead: () => void
  onDismiss: (id: string) => void
  onAcceptInvite?: (inviteId: string) => void
  onDeclineInvite?: (inviteId: string) => void
}

export const NotificationsDrawer: React.FC<NotificationsDrawerProps> = ({
  isOpen,
  onClose,
  notifications,
  onClearAll,
  onMarkAllRead,
  onDismiss,
  onAcceptInvite,
  onDeclineInvite,
}) => {
  if (!isOpen) return null

  const unreadCount = notifications.filter((n) => !n.read).length

  const getTypeBadge = (type: SystemNotification['type']) => {
    switch (type) {
      case 'security':
        return { label: 'Security Gate', color: '#ef4444' }
      case 'order':
        return { label: 'Freelance Workspace', color: '#10b981' }
      case 'research':
        return { label: 'Strawberry AI', color: '#10b981' }
      case 'project_invite':
        return { label: 'Project Invitation', color: '#047857' }
      default:
        return { label: 'System Event', color: '#047857' }
    }
  }

  return (
    <div
      className="notifications-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Activity and Notifications"
      data-testid="notifications-drawer-backdrop"
    >
      <div
        className="notifications-panel"
        onClick={(e) => e.stopPropagation()}
        data-testid="notifications-panel"
      >
        <div className="notif-header">
          <div className="notif-title-group">
            <h3 className="notif-title">Activity Center</h3>
            {unreadCount > 0 && (
              <span className="notif-unread-badge" data-testid="unread-count-badge">
                {unreadCount} new
              </span>
            )}
          </div>
          <button
            type="button"
            className="notif-close-btn"
            onClick={onClose}
            aria-label="Close activity center"
            data-testid="close-notif-btn"
          >
            ✕
          </button>
        </div>

        <div className="notif-toolbar">
          <button
            type="button"
            className="notif-action-btn"
            onClick={onMarkAllRead}
            disabled={unreadCount === 0}
            data-testid="mark-all-read-btn"
          >
            Mark all read
          </button>
          <button
            type="button"
            className="notif-action-btn danger"
            onClick={onClearAll}
            disabled={notifications.length === 0}
            data-testid="clear-all-notif-btn"
          >
            Clear log
          </button>
        </div>

        <div className="notif-list" role="list">
          {notifications.length === 0 ? (
            <div className="notif-empty" data-testid="notif-empty-state">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
              <p>No recent activity notifications</p>
              <span>All autonomous workspaces and security gates are nominal.</span>
            </div>
          ) : (
            notifications.map((item) => {
              const badge = getTypeBadge(item.type)
              return (
                <div
                  key={item.id}
                  className={`notif-item ${!item.read ? 'unread' : ''}`}
                  data-testid={`notif-item-${item.id}`}
                  role="listitem"
                >
                  <div className="notif-item-top">
                    <span
                      className="notif-badge"
                      style={{ color: badge.color, borderColor: `${badge.color}40` }}
                    >
                      {badge.label}
                    </span>
                    <span className="notif-time">{item.timestamp}</span>
                    <button
                      type="button"
                      className="notif-item-dismiss"
                      onClick={() => onDismiss(item.id)}
                      aria-label="Dismiss notification"
                      title="Dismiss"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="notif-item-title">{item.title}</div>
                  <p className="notif-item-msg">{item.message}</p>
                  {(item.type === 'project_invite' || item.inviteId) && (
                    <div className="notif-invite-action-row">
                      <button
                        type="button"
                        className="notif-accept-invite-btn"
                        onClick={() => onAcceptInvite?.(item.inviteId || item.id)}
                        data-testid={`accept-invite-btn-${item.id}`}
                      >
                        ✓ Accept & Join
                      </button>
                      <button
                        type="button"
                        className="notif-decline-invite-btn"
                        onClick={() => onDeclineInvite?.(item.inviteId || item.id)}
                        data-testid={`decline-invite-btn-${item.id}`}
                      >
                        Decline
                      </button>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
