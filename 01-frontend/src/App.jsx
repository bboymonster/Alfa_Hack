import Header from './components/Header'
import NewsCard from './components/NewsCard'

function App() {
  return (
    <div className="min-h-screen bg-slate-900">
      <Header />
      
      <main className="max-w-5xl mx-auto px-4 pb-12">
        <h1 className="text-2xl font-bold text-white mb-6">Лента «Новость-Инсайт»</h1>
        
        <NewsCard />
        <NewsCard />
      </main>
    </div>
  )
}

export default App