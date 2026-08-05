import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDomains, useCreateDomain, useDeleteDomain, useTriggerCheck } from '../hooks/useDomains'
import { useLogout } from '../hooks/useAuth'
import type { Domain } from '@/types'

export function DashboardPage() {
  const navigate = useNavigate()
  const logout = useLogout()
  const [showAddModal, setShowAddModal] = useState(false)
  
  const { data: domainsData, isLoading } = useDomains()
  const createDomain = useCreateDomain()
  const deleteDomain = useDeleteDomain()
  const triggerCheck = useTriggerCheck()
  
  const domains: Domain[] = domainsData?.data || []
  
  const handleAddDomain = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const url = formData.get('url') as string
    const name = formData.get('name') as string
    
    try {
      await createDomain.mutateAsync({ url, name: name || undefined })
      setShowAddModal(false)
      e.currentTarget.reset()
    } catch (error) {
      console.error('Failed to create domain:', error)
    }
  }
  
  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this domain?')) {
      await deleteDomain.mutateAsync(id)
    }
  }
  
  const handleTriggerCheck = async (id: number) => {
    await triggerCheck.mutateAsync(id)
    alert('Lighthouse check triggered! Results will be available shortly.')
  }
  
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">🚀 Monitor App v2</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowAddModal(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
              >
                + Add Domain
              </button>
              <button
                onClick={logout}
                className="text-gray-600 hover:text-gray-900"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <span className="text-2xl">🌐</span>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Total Domains
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {domains.length}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <span className="text-2xl">✅</span>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Active Domains
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {domains.filter(d => d.is_active).length}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <span className="text-2xl">⚡</span>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        Avg Performance
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {domains.length > 0 ? '—' : '0'}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Domains Table */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Your Domains
              </h3>
            </div>
            <div className="border-t border-gray-200">
              {domains.length === 0 ? (
                <div className="px-4 py-12 text-center">
                  <span className="text-4xl mb-4 block">📭</span>
                  <p className="text-gray-500">No domains yet. Add your first domain to start monitoring!</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Domain
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Check Interval
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {domains.map((domain) => (
                        <tr key={domain.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {domain.name || domain.url}
                            </div>
                            <div className="text-sm text-gray-500">
                              {domain.url}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                              domain.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {domain.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {domain.check_interval_minutes} min
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                            <button
                              onClick={() => handleTriggerCheck(domain.id)}
                              className="text-indigo-600 hover:text-indigo-900"
                            >
                              Check Now
                            </button>
                            <button
                              onClick={() => navigate(`/domains/${domain.id}`)}
                              className="text-blue-600 hover:text-blue-900"
                            >
                              Details
                            </button>
                            <button
                              onClick={() => handleDelete(domain.id)}
                              className="text-red-600 hover:text-red-900"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
      
      {/* Add Domain Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Add New Domain</h3>
            <form onSubmit={handleAddDomain}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    URL *
                  </label>
                  <input
                    type="url"
                    name="url"
                    required
                    placeholder="https://example.com"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Name (optional)
                  </label>
                  <input
                    type="text"
                    name="name"
                    placeholder="My Website"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
              </div>
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createDomain.isPending}
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  {createDomain.isPending ? 'Adding...' : 'Add Domain'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
