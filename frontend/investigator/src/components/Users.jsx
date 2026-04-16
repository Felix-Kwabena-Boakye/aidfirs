// Users.jsx removed as unused in investigator App.jsx

import { usersAPI } from '../api';
import { Shield, ShieldAlert, CheckCircle, XCircle, UserPlus } from 'lucide-react';

export default function Users() { // REMOVED: Not used in investigator
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [currentUser, setCurrentUser] = useState(null);

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
            console.error('Error fetching users:', err);
            setError('Failed to load users. You may not have permission.');
        } finally {
            setLoading(false);
        }
    };

    const handleActivate = async (userId) => {
        try {
            await usersAPI.activateUser(userId);
            // Refresh the users list
            fetchUsers();
        } catch (err) {
            console.error('Error activating user:', err);
            alert('Failed to activate user. Please try again.');
        }
    };

    const handleDeactivate = async (userId) => {
        if (window.confirm('Are you sure you want to deactivate this user? They will not be able to log in.')) {
            try {
                await usersAPI.deactivateUser(userId);
                // Refresh the users list
                fetchUsers();
            } catch (err) {
                console.error('Error deactivating user:', err);
                alert('Failed to deactivate user. Please try again.');
            }
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 m-6">
                <p className="text-red-700">{error}</p>
            </div>
        );
    }

    const pendingUsers = users.filter(user => !user.is_active);
    const activeUsers = users.filter(user => user.is_active);

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-gray-800">User Management</h1>
            </div>

            {pendingUsers.length > 0 && (
                <div className="bg-white rounded-lg shadow-sm border border-yellow-200 overflow-hidden">
                    <div className="bg-yellow-50 px-6 py-4 border-b border-yellow-200 flex items-center gap-3">
                        <ShieldAlert className="text-yellow-600" size={24} />
                        <h2 className="text-lg font-semibold text-yellow-800">Pending Approvals ({pendingUsers.length})</h2>
                    </div>
                    <div className="divide-y divide-gray-200">
                        {pendingUsers.map(user => (
                            <div key={user._id || user.username} className="p-6 flex items-center justify-between hover:bg-gray-50 bg-yellow-50/30 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className="bg-yellow-100 p-3 rounded-full text-yellow-600">
                                        <UserPlus size={24} />
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-medium text-gray-900">{user.first_name} {user.last_name}</h3>
                                        <div className="text-sm text-gray-500 flex items-center gap-2">
                                            <span>{user.email}</span>
                                            <span>&bull;</span>
                                            <span>{user.username}</span>
                                            <span>&bull;</span>
                                            <span className="capitalize font-medium text-yellow-700">Requested Role: {user.role}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => handleActivate(user._id)}
                                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors font-medium shadow-sm"
                                    >
                                        <CheckCircle size={18} />
                                        Approve & Activate
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                    <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                        <Shield size={20} className="text-gray-500" />
                        Active Users ({activeUsers.length})
                    </h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Joined</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Login</th>
                                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {activeUsers.map((user) => (
                                <tr key={user._id || user.username} className="hover:bg-gray-50 transition-colors">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">
                                                {user.first_name?.charAt(0) || user.username.charAt(0).toUpperCase()}
                                            </div>
                                            <div className="ml-4">
                                                <div className="text-sm font-medium text-gray-900">{user.first_name} {user.last_name}</div>
                                                <div className="text-sm text-gray-500">{user.email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                      ${user.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                                                user.role === 'investigator' ? 'bg-blue-100 text-blue-800' :
                                                    'bg-gray-100 text-gray-800'}`}>
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {user.date_joined ? new Date(user.date_joined).toLocaleDateString() : 'Unknown'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        {currentUser && currentUser.username !== user.username && user.username !== 'admin' && (
                                            <button
                                                onClick={() => handleDeactivate(user._id)}
                                                className="text-red-600 hover:text-red-900 flex items-center justify-end gap-1 ml-auto"
                                            >
                                                <XCircle size={16} />
                                                Deactivate
                                            </button>
                                        )}
                                        {(currentUser && currentUser.username === user.username) && (
                                            <span className="text-gray-400">Current User</span>
                                        )}
                                        {user.username === 'admin' && currentUser?.username !== 'admin' && (
                                            <span className="text-gray-400">System Admin</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
