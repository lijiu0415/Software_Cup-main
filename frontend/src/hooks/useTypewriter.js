import { useState, useRef, useEffect, useCallback } from 'react'

const CHAR_SPEED = 25
const PUNCTUATION_PAUSE = 80
const SENTENCE_PAUSE = 150

const isPunctuation = (char) => ',，;；:：'.includes(char)
const isSentenceEnd = (char) => '.。!！?？\n'.includes(char)

export default function useTypewriter() {
  const [displayedText, setDisplayedText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const queueRef = useRef([])
  const timerRef = useRef(null)
  const resolveRef = useRef(null)

  const processNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      clearInterval(timerRef.current)
      timerRef.current = null
      setIsTyping(false)
      if (resolveRef.current) {
        resolveRef.current()
        resolveRef.current = null
      }
      return
    }

    const char = queueRef.current.shift()
    setDisplayedText((prev) => prev + char)

    if (isSentenceEnd(char)) {
      clearInterval(timerRef.current)
      timerRef.current = setTimeout(() => {
        timerRef.current = setInterval(processNext, CHAR_SPEED)
      }, SENTENCE_PAUSE)
    } else if (isPunctuation(char)) {
      clearInterval(timerRef.current)
      timerRef.current = setTimeout(() => {
        timerRef.current = setInterval(processNext, CHAR_SPEED)
      }, PUNCTUATION_PAUSE)
    }
  }, [])

  const enqueue = useCallback((text) => {
    if (!text) return
    const chars = [...text]
    queueRef.current.push(...chars)

    if (!timerRef.current) {
      setIsTyping(true)
      timerRef.current = setInterval(processNext, CHAR_SPEED)
    }
  }, [processNext])

  const flush = useCallback(() => {
    if (queueRef.current.length > 0) {
      setDisplayedText((prev) => prev + queueRef.current.join(''))
      queueRef.current = []
    }
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setIsTyping(false)
  }, [])

  const reset = useCallback(() => {
    queueRef.current = []
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setDisplayedText('')
    setIsTyping(false)
    if (resolveRef.current) {
      resolveRef.current()
      resolveRef.current = null
    }
  }, [])

  const waitDone = useCallback(() => {
    return new Promise((resolve) => {
      if (!timerRef.current && queueRef.current.length === 0) {
        resolve()
        return
      }
      resolveRef.current = resolve
    })
  }, [])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  return { displayedText, isTyping, enqueue, flush, reset, waitDone }
}
