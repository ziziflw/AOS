import { createRoot } from 'react-dom/client'
import { GraphProvider } from './graph'
import { Shell } from './Shell'
import './shell.css'

createRoot(document.getElementById('root')!).render(<GraphProvider><Shell /></GraphProvider>)

