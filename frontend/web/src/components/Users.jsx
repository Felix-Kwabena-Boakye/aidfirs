import React, { useState, useEffect } from 'react';
import { usersAPI } from '../api';
import { Shield, ShieldAlert, CheckCircle, XCircle, UserPlus, KeyRound } from 'lucide-react';
import { toast } from 'sonner';

export default function Users() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [currentUser, setCurrentUser] = useState(null);

    // Password reset modal state
    const [resetModal, setResetModal] = useState({ open: false, userId: null, userName: '' });
    const [newPassword, setNewPassword] = useState('');
    const [resetting, setResetting] = useState(false);

    useEffect(() => {
        const userStr = localStorage.getItem('user');
        if (userStr) {
            setCurrentUser(JSON.parse(userStr));
        }
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            setLoading(true);
            const response = await usersAPI.getUsers();
            setUsers(response.data);
            setError('');
        } catch (err) {
            toast.error('Failed to load users. You may not have permission.');
        } finally {
            setLoading(false);
        }
    };

    const handleActivate = async (userId, userName) => {
        try {
            await usersAPI.activateUser(userId);
            toast.success(`✅ ${userName}'s account has been approved and activated.`);
            fetchUsers();
        } catch (err) {
            toast.error('Failed to activate user. Please try again.');
        }
    };

    const handleDeactivate = async (userId, userName) => {
        if (window.confirm(`Deactivate ${userName}'s account? They will not be able to log in.`)) {
            try {
                await usersAPI.deactivateUser(userId);
                toast.success(`${userName}'s account has been deactivated.`);
                fetchUsers();
            } catch (err) {
                toast.error('Failed to deactivate user. Please try again.');
            }
        }
    };

    const handleReject = async (userId, userName) => {
        if (window.confirm(`Reject and delete ${userName}'s registration request?`)) {
            try {
                await usersAPI.deactivateUser(userId);
                toast.success(`${userName}'s registration has been rejected.`);
                fetchUsers();
            } catch (err) {
                toast.error('Failed to reject user. Please try again.');
            }
        }
    };

    const openResetModal = (userId, userName) => {
        setResetModal({ open: true, userId, userName });
        setNewPassword('');
    };

    const closeResetModal = () => {
        setResetModal({ open: false, userId: null, userName: '' });
        setNewPassword('');
    };

    const handleResetPassword = async () => {
        if (newPassword.length < 6) {
            toast.error('Password must be at least 6 characters.');
            return;
        }
        setResetting(true);
        try {
            await usersAPI.resetPassword(resetModal.userId, newPassword);
            toast.success(`✅ Password for ${resetModal.userName} has been reset successfully.`);
            closeResetModal();
        } catch (err) {
            toast.error('Failed to reset password. Please try again.');
        } finally {
            setResetting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    // Error handled by toast

    const pendingUsers = users.filter(user => !user.is_active);
    const activeUsers = users.filter(user => user.is_active);

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-white">User Management</h1>
            </div>

            {pendingUsers.length > 0 && (
                <div className="bg-gray-800 rounded-xl shadow-xl border border-amber-500/20 overflow-hidden">
                    <div className="bg-amber-950/20 px-6 py-4 border-b border-amber-500/20 flex items-center gap-3">
                        <ShieldAlert className="text-amber-400" size={24} />
                        <h2 className="text-lg font-semibold text-amber-300">Pending Approvals ({pendingUsers.length})</h2>
                    </div>
                    <div className="divide-y divide-gray-700 bg-gray-850">
                        {pendingUsers.map(user => (
                            <div key={user._id || user.username} className="p-6 flex items-center justify-between hover:bg-gray-700/30 bg-amber-950/5 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className="bg-amber-500/10 p-3 rounded-full text-amber-400 border border-amber-500/20">
                                        <UserPlus size={24} />
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-medium text-white">{user.first_name} {user.last_name}</h3>
                                        <div className="text-sm text-gray-400 flex items-center gap-2 mt-1">
                                            <span>{user.email}</span>
                                            <span>&bull;</span>
                                            <span className="font-mono text-xs">{user.username}</span>
                                            <span>&bull;</span>
                                            <span className="capitalize font-medium text-amber-400">Requested Role: {user.role}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => handleActivate(user._id, user.username)}
                                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-colors font-medium shadow-sm"
                                    >
                                        <CheckCircle size={18} />
                                        Approve &amp; Activate
                                    </button>
                                    <button
                                        onClick={() => openResetModal(user._id, user.username)}
                                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors font-medium shadow-sm"
                                    >
                                        <KeyRound size={18} />
                                        Set Password
                                    </button>
                                    <button
                                        onClick={() => handleReject(user._id, user.username)}
                                        className="flex items-center gap-2 px-4 py-2 bg-red-950/45 text-red-400 border border-red-500/20 rounded-xl hover:bg-red-900 hover:text-white transition-colors font-medium"
                                    >
                                        <XCircle size={18} />
                                        Reject
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="bg-gray-800 rounded-xl shadow-xl border border-gray-700 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-700 flex justify-between items-center bg-gray-900/30">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Shield size={20} className="text-blue-400" />
                        Active Users ({activeUsers.length})
                    </h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-700">
                        <thead className="bg-gray-900/50">
                            <tr>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">User</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Role</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Joined</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Last Login</th>
                                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-gray-800 divide-y divide-gray-700">
                            {activeUsers.map((user) => (
                                <tr key={user._id || user.username} className="hover:bg-gray-700/30 transition-colors">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <div className="flex-shrink-0 h-10 w-10 bg-blue-950/50 border border-blue-500/20 rounded-full flex items-center justify-center text-blue-400 font-bold">
                                                {user.first_name?.charAt(0) || user.username.charAt(0).toUpperCase()}
                                            </div>
                                            <div className="ml-4">
                                                <div className="text-sm font-medium text-white">{user.first_name} {user.last_name}</div>
                                                <div className="text-sm text-gray-400">{user.email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full border 
                      ${user.role === 'admin' ? 'bg-purple-950/30 text-purple-400 border-purple-500/20' :
                                                user.role === 'investigator' ? 'bg-blue-950/30 text-blue-400 border-blue-500/20' :
                                                    'bg-gray-900 text-gray-400 border-gray-700'}`}>
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                                        {user.date_joined ? new Date(user.date_joined).toLocaleDateString() : 'Unknown'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                                        {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        {currentUser && currentUser.username !== user.username && (
                                            <div className="flex items-center justify-end gap-3">
                                                {user.username !== 'admin' && (
                                                    <>
                                                        <button
                                                            onClick={() => openResetModal(user._id, user.username)}
                                                            className="flex items-center gap-1 text-blue-400 hover:text-blue-300 transition-colors"
                                                            title="Reset Password"
                                                        >
                                                            <KeyRound size={15} />
                                                            Reset Password
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeactivate(user._id, user.username)}
                                                            className="flex items-center gap-1 text-red-400 hover:text-red-300 transition-colors"
                                                        >
                                                            <XCircle size={15} />
                                                            Deactivate
                                                        </button>
                                                    </>
                                                )}
                                                {user.username === 'admin' && currentUser?.username !== 'admin' && (
                                                    <span className="text-gray-500">System Admin</span>
                                                )}
                                            </div>
                                        )}
                                        {currentUser && currentUser.username === user.username && (
                                            <span className="text-gray-500">Current User</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Reset Password Modal */}
            {resetModal.open && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl p-6 w-full max-w-md mx-4">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-2 bg-blue-950 border border-blue-500/20 rounded-full">
                                <KeyRound className="text-blue-400" size={22} />
                            </div>
                            <div>
                                <h3 className="text-lg font-semibold text-white">Reset Password</h3>
                                <p className="text-sm text-gray-400">Set a new password for <span className="font-medium text-gray-200">{resetModal.userName}</span></p>
                            </div>
                        </div>
                        <input
                            type="password"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleResetPassword()}
                            placeholder="Enter new password (min. 6 characters)"
                            className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 mb-5"
                            autoFocus
                        />
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={closeResetModal}
                                disabled={resetting}
                                className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-900 border border-gray-700 rounded-xl hover:bg-gray-700 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleResetPassword}
                                disabled={resetting || newPassword.length < 6}
                                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {resetting ? (
                                    <><span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full inline-block"></span> Resetting...</>
                                ) : (
                                    <><KeyRound size={15} /> Reset Password</>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
