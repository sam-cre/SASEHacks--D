import { useState } from 'react'
import './App.css'
import Header from './src/components/Header'
import { motion, AnimatePresence } from 'framer-motion'

const menuItems = [
  { id: 'flashcards', label: 'FLASHCARDS' },
  { id: 'dungeon',    label: 'ENTER THE DUNGEON' },
  { id: 'settings',  label: 'SETTINGS' },
]

function App() {
  const [showMenu, setShowMenu] = useState(false)
  const [selected, setSelected] = useState(0)

  return (
    <>
      <Header />
      <div className="arcade-room">
        <motion.div
          className="arcade-cabinet"
          initial={{ scale: 0.7, y: 50, opacity: 0 }}
          animate={{ scale: 1, y: 0, opacity: 1 }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        >
          <div className="crt-screen">
            <AnimatePresence mode="wait">
              {!showMenu ? (
                <motion.button
                  key="start"
                  className="start-btn"
                  exit={{ opacity: 0, scale: 0.8 }}
                  whileHover={{ scale: 1.08 }}
                  whileTap={{ scale: 0.92 }}
                  onClick={() => setShowMenu(true)}
                >
                  START
                </motion.button>
              ) : (
                <motion.div
                  key="menu"
                  className="pixel-menu"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.25 }}
                >
                  <div className="pixel-menu-title">— SELECT —</div>
                  <div className="pixel-menu-list">
                    {menuItems.map((item, i) => (
                      <div
                        key={item.id}
                        className={`pixel-menu-item${selected === i ? ' active' : ''}`}
                        onMouseEnter={() => setSelected(i)}
                        onClick={() => console.log(item.id)}
                      >
                        <span className="pixel-arrow">{selected === i ? '▶' : '\u00A0'}</span>
                        {item.label}
                      </div>
                    ))}
                  </div>
                  <div className="pixel-menu-back" onClick={() => setShowMenu(false)}>
                    ← BACK
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      </div>
    </>
  )
}

export default App
