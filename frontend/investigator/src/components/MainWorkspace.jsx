export default function MainWorkspace({ children }) {
  return (
    <main className="flex-1 overflow-auto bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {children}
      </div>
    </main>
  )
}
