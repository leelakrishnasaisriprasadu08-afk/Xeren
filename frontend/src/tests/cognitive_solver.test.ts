import { describe, it, expect } from 'vitest'
import { solveAnything } from '../services/cognitiveSolver'

describe('Cognitive Problem Solver & Conversational Engine', () => {
  it('solves linear algebraic equations with step-by-step resolution', () => {
    const res = solveAnything('solve 2x + 5 = 15')
    expect(res).toContain('Mathematical Solution')
    expect(res).toContain('x = 5')

    const res2 = solveAnything('3y - 9 = 12')
    expect(res2).toContain('y = 7')
  })

  it('solves arithmetic calculations', () => {
    const res = solveAnything('calculate 25 * 4 + 10')
    expect(res).toContain('110')
  })

  it('generates prime number algorithms when explicitly asked for code', () => {
    const res = solveAnything('write a python function to find prime numbers')
    expect(res).toContain('def is_prime')
    expect(res).toContain('math.isqrt')
  })

  it('solves string reversal and palindrome requests', () => {
    const res = solveAnything('reverse a string and check palindrome')
    expect(res).toContain('reverse_string')
    expect(res).toContain('is_palindrome')
  })

  it('generates React components', () => {
    const res = solveAnything('create a modern react button counter component')
    expect(res).toContain('ModernCounterCard')
    expect(res).toContain('useState')
  })

  it('produces clean non-LaTeX output without unrendered math symbols', () => {
    const res = solveAnything('write a python function to find prime numbers')
    expect(res).not.toContain('\\sqrt')
    expect(res).not.toContain('$$')
    expect(res).not.toContain('\\mathbf')
    expect(res).toContain('O(√n)')

    const mathRes = solveAnything('solve 2x + 5 = 15')
    expect(mathRes).not.toContain('$$')
    expect(mathRes).not.toContain('\\mathbf')
    expect(mathRes).toContain('**x = 5**')
  })

  it('correctly answers how many states are in India without Python code', () => {
    const res = solveAnything('how many states are there in india')
    expect(res).toContain('28 States')
    expect(res).toContain('8 Union Territories')
    expect(res).toContain('New Delhi')
    // Crucial: Must NOT output Python code blocks or dummy task functions
    expect(res).not.toContain('def execute_task')
    expect(res).not.toContain('```python')
  })

  it('correctly answers queries about Andhra Pradesh districts and heritage without Python code', () => {
    const res = solveAnything('about states in ap')
    expect(res).toContain('Andhra Pradesh')
    expect(res).toContain('26 Districts')
    expect(res).toContain('Amaravati')
    expect(res).toContain("Vignan's Lara Institute of Technology & Science")
    expect(res).not.toContain('def execute_task')
    expect(res).not.toContain('```python')
  })

  it('correctly answers Xeren creators and identity without dummy code', () => {
    const res = solveAnything('who created xeren')
    expect(res).toContain('Leela Krishna')
    expect(res).toContain('Pallavi')
    expect(res).toContain('Dinesh Kumar')
    expect(res).toContain('Manideep')
    expect(res).toContain('Yaswanth')
    expect(res).toContain('Guna Bhargav')
    expect(res).toContain("Vignan's Lara Institute of Technology & Science")
    expect(res).not.toContain('def execute_task')
  })

  it('answers general knowledge questions conversationally without dummy scripts', () => {
    const res = solveAnything('what is docker')
    expect(res).toContain('containerization platform')
    expect(res).not.toContain('def execute_task')
  })

  it('greets naturally on "hlo" and informal greetings without robotic canned templates', () => {
    const res = solveAnything('hlo')
    expect(res).toContain('Hello! I am Xeren ⚡')
    expect(res).not.toContain('Insights & Analysis for: "hlo"')
    expect(res).not.toContain('states in India')

    const res2 = solveAnything('helo xeren')
    expect(res2).toContain('Hello! I am Xeren ⚡')
    expect(res2).not.toContain('Insights & Analysis')
  })
})
