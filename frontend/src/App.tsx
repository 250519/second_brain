import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ToastProvider } from './components/ui/Toast'
import { Shell } from './components/layout/Shell'
import { DashboardPage } from './pages/DashboardPage'
import { IngestPage } from './pages/IngestPage'
import { QueryPage } from './pages/QueryPage'
import { WikiPage } from './pages/WikiPage'
import { WikiPageDetail } from './pages/WikiPageDetail'
import { GraphPage } from './pages/GraphPage'
import { IdeasPage } from './pages/IdeasPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Shell />}>
              <Route index element={<DashboardPage />} />
              <Route path="ingest" element={<IngestPage />} />
              <Route path="query" element={<QueryPage />} />
              <Route path="wiki" element={<WikiPage />}>
                <Route path=":type/:slug" element={<WikiPageDetail />} />
              </Route>
              <Route path="graph" element={<GraphPage />} />
              <Route path="ideas" element={<IdeasPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}
