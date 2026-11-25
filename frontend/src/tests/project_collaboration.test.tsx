import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { NewProjectModal } from '../components/NewProjectModal/NewProjectModal'
import { AuthDashboardModal } from '../components/AuthDashboardModal/AuthDashboardModal'
import { NotificationsDrawer, type SystemNotification } from '../components/NotificationsDrawer/NotificationsDrawer'
import { TopHeader } from '../components/TopHeader/TopHeader'
import type { UserProfile } from '../types/auth'

const mockUser: UserProfile = {
  user_id: 'usr_test_01',
  handle: '@xeren_dev',
  display_name: 'Lead Architect',
  email: 'developer@xeren.ai',
  phone_number: '+1 (555) 019-2834',
  avatar_url: 'https://example.com/avatar.jpg',
  plan_tier: 'Pro Studio',
  linked_methods: ['google', 'github', 'passkey'],
  passkeys: [
    {
      credential_id: 'cred_test_01',
      device_name: 'Windows Hello / Security Key',
      public_key: 'p256_mock_key',
      created_at: '2026-09-07T12:00:00Z',
      last_used_at: '2026-09-07T12:00:00Z',
    },
  ],
  active_project_id: 'proj_01',
  created_at: '2026-09-07T12:00:00Z',
  last_login_at: '2026-09-07T12:00:00Z',
}

describe('Project Collaboration & Multi-Method Auth Systems', () => {
  // -------------------------------------------------------------
  // 1. New Project Modal: Solo vs Group & Member Invitations
  // -------------------------------------------------------------
  describe('NewProjectModal', () => {
    it('renders both Solo and Group project options initially', () => {
      render(
        <NewProjectModal
          isOpen={true}
          onClose={vi.fn()}
          currentUser={mockUser}
          onCreateProject={vi.fn()}
        />
      )

      expect(screen.getByTestId('new-project-modal')).toBeInTheDocument()
      expect(screen.getByTestId('project-type-solo')).toBeInTheDocument()
      expect(screen.getByTestId('project-type-group')).toBeInTheDocument()
      expect(screen.getByText('Solo Project')).toBeInTheDocument()
      expect(screen.getByText('Group Project')).toBeInTheDocument()
    })

    it('navigates to Solo Project configuration and creates solo workspace', async () => {
      const onCreateProject = vi.fn().mockResolvedValue({})
      render(
        <NewProjectModal
          isOpen={true}
          onClose={vi.fn()}
          currentUser={mockUser}
          onCreateProject={onCreateProject}
        />
      )

      // Click Solo card
      fireEvent.click(screen.getByTestId('select-solo-btn'))

      // Should show Solo config form
      expect(screen.getByTestId('project-config-form')).toBeInTheDocument()
      expect(screen.getByTestId('project-name-input')).toBeInTheDocument()
      expect(screen.getByTestId('create-solo-project-btn')).toBeInTheDocument()

      // Submit
      fireEvent.click(screen.getByTestId('create-solo-project-btn'))
      await waitFor(() => {
        expect(onCreateProject).toHaveBeenCalledWith(
          expect.objectContaining({
            project_type: 'solo',
          })
        )
      })
    })

    it('navigates to Group Project configuration with Xeren account and Email member invitations', async () => {
      const onCreateProject = vi.fn().mockResolvedValue({})
      render(
        <NewProjectModal
          isOpen={true}
          onClose={vi.fn()}
          currentUser={mockUser}
          onCreateProject={onCreateProject}
        />
      )

      // Click Group card
      fireEvent.click(screen.getByTestId('select-group-btn'))

      expect(screen.getByTestId('group-invitation-section')).toBeInTheDocument()
      expect(screen.getByTestId('tab-invite-xeren')).toBeInTheDocument()
      expect(screen.getByTestId('tab-invite-email')).toBeInTheDocument()

      // 1. Add member via Xeren account handle
      fireEvent.click(screen.getByTestId('tab-invite-xeren'))
      const handleInput = screen.getByTestId('invite-xeren-handle-input')
      fireEvent.change(handleInput, { target: { value: '@sarah_ai' } })
      fireEvent.click(screen.getByTestId('send-xeren-invite-btn'))

      expect(screen.getByText('@sarah_ai')).toBeInTheDocument()
      expect(screen.getByText(/In-App Notification Queued/i)).toBeInTheDocument()

      // 2. Add member via Email account
      fireEvent.click(screen.getByTestId('tab-invite-email'))
      const emailInput = screen.getByTestId('invite-email-input')
      fireEvent.change(emailInput, { target: { value: 'remote_dev@partner.com' } })
      fireEvent.click(screen.getByTestId('send-email-invite-btn'))

      expect(screen.getByText('remote_dev@partner.com')).toBeInTheDocument()
      expect(screen.getAllByText(/Email Verification Link/i).length).toBeGreaterThan(0)

      // Submit group project
      fireEvent.click(screen.getByTestId('create-group-project-btn'))
      await waitFor(() => {
        expect(onCreateProject).toHaveBeenCalledWith(
          expect.objectContaining({
            project_type: 'group',
            initial_invites: expect.arrayContaining([
              expect.objectContaining({ target: '@sarah_ai', invite_type: 'xeren_account' }),
              expect.objectContaining({ target: 'remote_dev@partner.com', invite_type: 'email' }),
            ]),
          })
        )
      })
    })
  })

  // -------------------------------------------------------------
  // 2. Multi-Method Auth Dashboard (Google, GitHub, Facebook, Passkey, OTP)
  // -------------------------------------------------------------
  describe('AuthDashboardModal', () => {
    it('renders social buttons including Facebook and triggers social login', () => {
      const onSocialLogin = vi.fn()
      render(
        <AuthDashboardModal
          isOpen={true}
          onClose={vi.fn()}
          currentUser={mockUser}
          onUpdateProfile={vi.fn()}
          onSocialLogin={onSocialLogin}
          onPasskeyAuth={vi.fn()}
          onRegisterPasskey={vi.fn()}
          onSendOtp={vi.fn()}
          onVerifyOtp={vi.fn()}
        />
      )

      expect(screen.getByTestId('auth-btn-google')).toBeInTheDocument()
      expect(screen.getByTestId('auth-btn-github')).toBeInTheDocument()
      expect(screen.getByTestId('auth-btn-facebook')).toBeInTheDocument()
      expect(screen.getByTestId('auth-btn-passkey')).toBeInTheDocument()

      // Click Facebook login
      fireEvent.click(screen.getByTestId('auth-btn-facebook'))
      expect(onSocialLogin).toHaveBeenCalledWith('facebook')

      // Click Google login
      fireEvent.click(screen.getByTestId('auth-btn-google'))
      expect(onSocialLogin).toHaveBeenCalledWith('google')
    })

    it('handles Passkey authentication and new device registration', async () => {
      const onPasskeyAuth = vi.fn().mockResolvedValue(undefined)
      const onRegisterPasskey = vi.fn().mockResolvedValue(undefined)

      render(
        <AuthDashboardModal
          isOpen={true}
          onClose={vi.fn()}
          currentUser={mockUser}
          onUpdateProfile={vi.fn()}
          onSocialLogin={vi.fn()}
          onPasskeyAuth={onPasskeyAuth}
          onRegisterPasskey={onRegisterPasskey}
          onSendOtp={vi.fn()}
          onVerifyOtp={vi.fn()}
        />
      )

      // Test passkey unlock
      fireEvent.click(screen.getByTestId('auth-btn-passkey'))
      expect(onPasskeyAuth).toHaveBeenCalled()

      // Test passkey registration toggle
      fireEvent.click(screen.getByTestId('toggle-register-passkey'))
      expect(screen.getByTestId('passkey-device-input')).toBeInTheDocument()

      fireEvent.change(screen.getByTestId('passkey-device-input'), {
        target: { value: 'YubiKey 5 NFC' },
      })
      fireEvent.click(screen.getByTestId('submit-passkey-register'))

      await waitFor(() => {
        expect(onRegisterPasskey).toHaveBeenCalledWith('YubiKey 5 NFC')
      })
    })

    it('handles Code to Email passwordless OTP verification', async () => {
      const onSendOtp = vi.fn().mockResolvedValue('559102')
      const onVerifyOtp = vi.fn().mockResolvedValue(true)

      render(
        <AuthDashboardModal
          isOpen={true}
          onClose={vi.fn()}
          currentUser={mockUser}
          onUpdateProfile={vi.fn()}
          onSocialLogin={vi.fn()}
          onPasskeyAuth={vi.fn()}
          onRegisterPasskey={vi.fn()}
          onSendOtp={onSendOtp}
          onVerifyOtp={onVerifyOtp}
        />
      )

      // Switch to Code to Email tab
      fireEvent.click(screen.getByTestId('auth-tab-email'))
      expect(screen.getByTestId('pane-email')).toBeInTheDocument()

      // Enter email and send code
      fireEvent.change(screen.getByTestId('email-otp-input'), {
        target: { value: 'teamlead@xeren.ai' },
      })
      fireEvent.click(screen.getByTestId('send-email-otp-btn'))

      await waitFor(() => {
        expect(onSendOtp).toHaveBeenCalledWith('teamlead@xeren.ai', 'email')
      })

      // Code entry field should now appear
      expect(screen.getByTestId('email-otp-code-input')).toBeInTheDocument()
      fireEvent.change(screen.getByTestId('email-otp-code-input'), {
        target: { value: '559102' },
      })
      fireEvent.click(screen.getByTestId('verify-email-otp-btn'))

      await waitFor(() => {
        expect(onVerifyOtp).toHaveBeenCalledWith('teamlead@xeren.ai', '559102', 'email')
      })
    })

    it('handles Code to Phone SMS OTP flow', async () => {
      const onSendOtp = vi.fn().mockResolvedValue('993412')
      const onVerifyOtp = vi.fn().mockResolvedValue(true)

      render(
        <AuthDashboardModal
          isOpen={true}
          onClose={vi.fn()}
          currentUser={mockUser}
          onUpdateProfile={vi.fn()}
          onSocialLogin={vi.fn()}
          onPasskeyAuth={vi.fn()}
          onRegisterPasskey={vi.fn()}
          onSendOtp={onSendOtp}
          onVerifyOtp={onVerifyOtp}
        />
      )

      // Switch to Code to Phone tab
      fireEvent.click(screen.getByTestId('auth-tab-phone'))
      expect(screen.getByTestId('pane-phone')).toBeInTheDocument()

      fireEvent.change(screen.getByTestId('phone-otp-input'), {
        target: { value: '+15550001122' },
      })
      fireEvent.click(screen.getByTestId('send-phone-otp-btn'))

      await waitFor(() => {
        expect(onSendOtp).toHaveBeenCalledWith('+15550001122', 'phone')
      })

      expect(screen.getByTestId('phone-otp-code-input')).toBeInTheDocument()
      fireEvent.change(screen.getByTestId('phone-otp-code-input'), {
        target: { value: '993412' },
      })
      fireEvent.click(screen.getByTestId('verify-phone-otp-btn'))

      await waitFor(() => {
        expect(onVerifyOtp).toHaveBeenCalledWith('+15550001122', '993412', 'phone')
      })
    })

    it('displays user profile details and allows saving updates', () => {
      const onUpdateProfile = vi.fn()
      render(
        <AuthDashboardModal
          isOpen={true}
          onClose={vi.fn()}
          currentUser={mockUser}
          onUpdateProfile={onUpdateProfile}
          onSocialLogin={vi.fn()}
          onPasskeyAuth={vi.fn()}
          onRegisterPasskey={vi.fn()}
          onSendOtp={vi.fn()}
          onVerifyOtp={vi.fn()}
        />
      )

      fireEvent.click(screen.getByTestId('auth-tab-profile'))
      expect(screen.getByText('Lead Architect')).toBeInTheDocument()
      expect(screen.getByText('@xeren_dev')).toBeInTheDocument()
      expect(screen.getByText('Pro Studio')).toBeInTheDocument()

      // Change display name
      fireEvent.change(screen.getByTestId('profile-display-name-input'), {
        target: { value: 'Principal Architect' },
      })
      fireEvent.click(screen.getByTestId('save-profile-btn'))

      expect(onUpdateProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          display_name: 'Principal Architect',
        })
      )
    })
  })

  // -------------------------------------------------------------
  // 3. Notifications Drawer: Project Invite with Accept/Decline
  // -------------------------------------------------------------
  describe('NotificationsDrawer Project Invites', () => {
    const inviteNotif: SystemNotification = {
      id: 'notif-inv-99',
      timestamp: 'Just now',
      title: 'Project Invitation: CyberForge AI',
      message: '@sarah_ai invited you to join the project as Editor',
      type: 'project_invite',
      read: false,
      inviteId: 'inv_cyberforge_99',
    }

    it('renders project invite notification with Accept and Decline buttons', () => {
      const onAcceptInvite = vi.fn()
      const onDeclineInvite = vi.fn()

      render(
        <NotificationsDrawer
          isOpen={true}
          onClose={vi.fn()}
          notifications={[inviteNotif]}
          onClearAll={vi.fn()}
          onMarkAllRead={vi.fn()}
          onDismiss={vi.fn()}
          onAcceptInvite={onAcceptInvite}
          onDeclineInvite={onDeclineInvite}
        />
      )

      expect(screen.getByText('Project Invitation: CyberForge AI')).toBeInTheDocument()
      const acceptBtn = screen.getByTestId('accept-invite-btn-notif-inv-99')
      const declineBtn = screen.getByTestId('decline-invite-btn-notif-inv-99')

      expect(acceptBtn).toBeInTheDocument()
      expect(declineBtn).toBeInTheDocument()

      fireEvent.click(acceptBtn)
      expect(onAcceptInvite).toHaveBeenCalledWith('inv_cyberforge_99')

      fireEvent.click(declineBtn)
      expect(onDeclineInvite).toHaveBeenCalledWith('inv_cyberforge_99')
    })
  })

  // -------------------------------------------------------------
  // 4. TopHeader Integration: New Project, Auth, and DB Version Handshake
  // -------------------------------------------------------------
  describe('TopHeader Navigation & Indicators', () => {
    it('renders New Project button, User Profile pill, and System Version pill', () => {
      const onOpenNewProject = vi.fn()
      const onOpenAuth = vi.fn()

      render(
        <TopHeader
          connectionState="connected"
          transportType="websocket"
          onOpenSettings={vi.fn()}
          onOpenNewProject={onOpenNewProject}
          onOpenAuth={onOpenAuth}
          currentUserHandle="@xeren_dev"
          dbConnected={true}
          dbMode="atlas"
          systemVersion="v1.2.0"
        />
      )

      // 1. New Project button
      const newProjBtn = screen.getByTestId('header-new-project-btn')
      expect(newProjBtn).toBeInTheDocument()
      fireEvent.click(newProjBtn)
      expect(onOpenNewProject).toHaveBeenCalled()

      // 2. User Profile button
      const userProfileBtn = screen.getByTestId('header-user-profile-btn')
      expect(userProfileBtn).toBeInTheDocument()
      expect(screen.getByText('@xeren_dev')).toBeInTheDocument()
      fireEvent.click(userProfileBtn)
      expect(onOpenAuth).toHaveBeenCalled()

      // 3. System Version Handshake pill
      const versionPill = screen.getByTestId('header-system-version-pill')
      expect(versionPill).toBeInTheDocument()
      expect(screen.getByText('v1.2.0')).toBeInTheDocument()
      expect(screen.getByText('Atlas')).toBeInTheDocument()
    })
  })
})
