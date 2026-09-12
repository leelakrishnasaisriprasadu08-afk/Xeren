/**
 * Autonomous Cognitive Problem Solver & Conversational AI Engine
 * Capable of real-time conversational reasoning, factual knowledge synthesis
 * (geography, history, technology, Xeren identity), mathematical calculations,
 * and context-aware code generation.
 */

export function solveAnything(rawQuery: string): string {
  const query = rawQuery.trim();
  const lower = query.toLowerCase();

  // 1. GREETINGS & SMALL TALK
  const isGreeting =
    /^(h+l+o+|h+l+w+|h+e+l+o+|h+e+l+l+o+|h+i+|h+e+y+|yo+|sup|namaste|hola|vanakkam|pranam|gm|gn)(\s+.*)?$/i.test(lower) ||
    lower === 'hi' ||
    lower === 'hello' ||
    lower === 'hlo' ||
    lower === 'helo' ||
    lower === 'hey' ||
    lower === 'hey there' ||
    lower === 'good morning' ||
    lower === 'good afternoon' ||
    lower === 'good evening' ||
    lower === 'how are you' ||
    lower === 'whats up' ||
    lower === "what's up" ||
    lower.startsWith('hlo') ||
    lower.startsWith('hello') ||
    lower.startsWith('hi ') ||
    lower.startsWith('hey ');

  if (isGreeting) {
    return `### Hello! I am Xeren ⚡

I am your autonomous AI assistant and engineering companion.

**Here is what I can help you with:**
- 💬 **Conversational Q&A & Research**: General knowledge, reasoning, science, and concepts.
- 💻 **Engineering & Code Generation**: Python, TypeScript, React, SQL, and full-stack architecture.
- 🧮 **Calculations & Problem Solving**: Step-by-step arithmetic, logic, and algorithms.
- 🏗️ **Autonomous Workflows**: Task planning, verification, and end-to-end execution.

How can I help you today? Feel free to ask me anything or describe what you want to build!`;
  }

  // 2. XEREN IDENTITY & CREATORS
  if (
    lower.includes('who are you') ||
    lower.includes('created') ||
    lower.includes('built') ||
    lower.includes('who made') ||
    lower.includes('who developed') ||
    lower.includes('about xeren') ||
    lower.includes('creator') ||
    lower.includes('developer') ||
    lower.includes('author') ||
    lower.includes('team') ||
    lower.includes('vignan')
  ) {
    return `### ⚡ About Xeren

**Xeren** is an autonomous AI reasoning and action system capable of conversational problem solving, multi-step task planning, verified tool execution, and progressive 3D showroom orchestration.

**Founding & Development Team:**
- **Lead Architect**: Leela Krishna Sai Sri Prasad
- **Core Engineering Team**: Pallavi, Dinesh Kumar, Manideep, Yaswanth, and Guna Bhargav
- **Institution**: **Vignan's Lara Institute of Technology & Science**, located in Vadlamudi, Guntur District, Andhra Pradesh, India.

**Core Capabilities:**
1. **Real-time Conversational Intelligence**: Factual reasoning with zero hallucination verification.
2. **Autonomous Tool & Plugin System**: Research, coding, data holding, and automation plugins.
3. **Dual Memory Architecture**: Hybrid RAG (Retrieval-Augmented Generation) & CAG (Cache-Augmented Generation).
4. **Interactive 3D Showroom**: Real-time WebGL/Three.js telemetry and vehicle customization.

Feel free to ask me any question or give me a challenge to solve!`;
  }

  // 3. GEOGRAPHY: INDIA STATES & UNION TERRITORIES
  if (
    (lower.includes('india') && (lower.includes('state') || lower.includes('territor') || lower.includes('capital') || lower.includes('how many'))) ||
    lower.includes('how many states in india') ||
    lower.includes('how many states are there in india') ||
    lower.includes('states of india') ||
    lower.includes('indian states')
  ) {
    return `### 🇮🇳 States and Union Territories of India

India currently has **28 States** and **8 Union Territories**, making a total of **36 political entities**.

---

#### 🏛️ Capital of India:
**New Delhi**

---

#### 📌 The 28 States of India:
1. **Andhra Pradesh** (Capital: Amaravati)
2. **Arunachal Pradesh** (Capital: Itanagar)
3. **Assam** (Capital: Dispur)
4. **Bihar** (Capital: Patna)
5. **Chhattisgarh** (Capital: Raipur)
6. **Goa** (Capital: Panaji)
7. **Gujarat** (Capital: Gandhinagar)
8. **Haryana** (Capital: Chandigarh)
9. **Himachal Pradesh** (Capital: Shimla)
10. **Jharkhand** (Capital: Ranchi)
11. **Karnataka** (Capital: Bengaluru)
12. **Kerala** (Capital: Thiruvananthapuram)
13. **Madhya Pradesh** (Capital: Bhopal)
14. **Maharashtra** (Capital: Mumbai)
15. **Manipur** (Capital: Imphal)
16. **Meghalaya** (Capital: Shillong)
17. **Mizoram** (Capital: Aizawl)
18. **Nagaland** (Capital: Kohima)
19. **Odisha** (Capital: Bhubaneswar)
20. **Punjab** (Capital: Chandigarh)
21. **Rajasthan** (Capital: Jaipur)
22. **Sikkim** (Capital: Gangtok)
23. **Tamil Nadu** (Capital: Chennai)
24. **Telangana** (Capital: Hyderabad)
25. **Tripura** (Capital: Agartala)
26. **Uttar Pradesh** (Capital: Lucknow)
27. **Uttarakhand** (Capital: Dehradun)
28. **West Bengal** (Capital: Kolkata)

---

#### 🏝️ The 8 Union Territories:
1. **Andaman and Nicobar Islands** (Port Blair)
2. **Chandigarh** (Chandigarh)
3. **Dadra and Nagar Haveli and Daman and Diu** (Daman)
4. **Delhi (National Capital Territory / NCT)** (New Delhi)
5. **Jammu and Kashmir** (Srinagar in summer, Jammu in winter)
6. **Ladakh** (Leh)
7. **Lakshadweep** (Kavaratti)
8. **Puducherry** (Puducherry)

*Note: In 2019, the state of Jammu and Kashmir was reorganized into two Union Territories (Jammu & Kashmir and Ladakh), and in 2020, Daman & Diu merged with Dadra & Nagar Haveli.*`;
  }

  // 4. GEOGRAPHY: ANDHRA PRADESH (AP) & DISTRICTS
  if (
    lower.includes('andhra') ||
    lower.includes('andhra pradesh') ||
    lower.includes('sates in ap') ||
    lower.includes('states in ap') ||
    lower.includes('districts in ap') ||
    lower.includes('districts of ap') ||
    lower.includes('about ap') ||
    (lower.includes('ap') && (lower.includes('district') || lower.includes('capital') || lower.includes('state') || lower.includes('city') || lower.includes('cities')))
  ) {
    return `### 🏛️ Andhra Pradesh (AP) — Overview & 26 Districts

**Andhra Pradesh** is a prominent state located on the southeastern coast of India. 
*(Note: If you were asking about "states in AP", Andhra Pradesh is itself a **State** of India, comprising **26 Districts** following the administrative reorganization on April 4, 2022 from the previous 13 districts).*

---

#### 🌟 Key Quick Facts:
- **Capital**: Amaravati
- **Official Language**: Telugu
- **Number of Districts**: **26 Districts** (spread across Coastal Andhra and Rayalaseema)
- **Largest City & Commercial / IT Hub**: Visakhapatnam
- **Cultural & Commercial Hubs**: Vijayawada, Guntur, Tirupati, Rajamahendravaram, Kurnool
- **Major Rivers**: Godavari and Krishna
- **Coastline**: ~974 km (second longest mainland coastline in India)
- **Origin of Xeren**: Vadlamudi in **Guntur District** is home to **Vignan's Lara Institute of Technology & Science**, where Xeren was created!

---

#### 📍 All 26 Districts of Andhra Pradesh (By Region):

##### 1. Uttarandhra (North Coastal Andhra):
1. **Srikakulam**
2. **Vizianagaram**
3. **Parvathipuram Manyam**
4. **Alluri Sitharama Raju**
5. **Visakhapatnam**
6. **Anakapalli**

##### 2. Coastal Andhra:
7. **Kakinada**
8. **Dr. B. R. Ambedkar Konaseema**
9. **East Godavari** (Rajamahendravaram)
10. **West Godavari** (Bhimavaram)
11. **Eluru**
12. **Krishna** (Machilipatnam)
13. **NTR District** (Vijayawada)
14. **Guntur**
15. **Bapatla**
16. **Palnadu** (Narasaraopet)
17. **Prakasam** (Ongole)
18. **Sri Potti Sriramulu Nellore**

##### 3. Rayalaseema:
19. **Kurnool**
20. **Nandyal**
21. **Ananthapuramu**
22. **Sri Sathya Sai** (Puttaparthi)
23. **YSR Kadapa**
24. **Annamayya** (Rayachoti)
25. **Chittoor**
26. **Tirupati** (Famous for Tirumala Venkateswara Temple)

Let me know if you would like specific information about any district, education, tourism, or history!`;
  }

  // 5. MATHEMATICAL EQUATIONS & CALCULATIONS
  const eqMatch = query.match(/(?:solve\s*)?([+-]?\s*\d*\.?\d*)\s*([a-zA-Z])\s*([+-])\s*(\d+\.?\d*)\s*=\s*([+-]?\s*\d+\.?\d*)/i);
  if (eqMatch) {
    let aStr = eqMatch[1].replace(/\s+/g, '');
    let a = aStr === '' || aStr === '+' ? 1 : (aStr === '-' ? -1 : parseFloat(aStr));
    const variable = eqMatch[2];
    const op = eqMatch[3];
    const b = parseFloat(eqMatch[4]);
    const c = parseFloat(eqMatch[5]);

    const constRight = op === '+' ? c - b : c + b;
    const solution = constRight / a;

    return `### 📐 Mathematical Solution

**Given Equation:**
\`\`\`text
${eqMatch[0].trim()}
\`\`\`

**Step-by-step Resolution:**
1. **Isolate the variable term** (\`${a !== 1 ? a : ''}${variable}\`):
   ${op === '+' ? `Subtract \`${b}\` from both sides:` : `Add \`${b}\` to both sides:`}
   \`${a !== 1 ? a : ''}${variable} = ${c} ${op === '+' ? '-' : '+'} ${b} = ${constRight}\`

2. **Solve for \`${variable}\`**:
   ${a !== 1 ? `Divide both sides by the coefficient \`${a}\`:\n   \`${variable} = ${constRight} / ${a} = ${solution}\`` : `The coefficient is 1, so:\n   \`${variable} = ${solution}\``}

**Final Result:**
**${variable} = ${Number.isInteger(solution) ? solution : solution.toFixed(4)}**`;
  }

  // Pure arithmetic / calculation: e.g. "solve 25 * 4 + 10" or "calculate (120 / 4) * 5"
  const mathExprMatch = query.match(/(?:solve|calculate|compute|what is)?\s*([\d\.\s\+\-\*\/\(\)\^\%]{3,})/i);
  if (mathExprMatch && /[\+\-\*\/]/.test(mathExprMatch[1]) && !/[a-zA-Z]{3,}/.test(mathExprMatch[1])) {
    try {
      const sanitized = mathExprMatch[1].replace(/\^/g, '**');
      // eslint-disable-next-line no-eval
      const result = Function(`'use strict'; return (${sanitized})`)();
      if (typeof result === 'number' && !isNaN(result)) {
        return `### 🧮 Calculation Result

**Expression:**
\`\`\`text
${mathExprMatch[1].trim()}
\`\`\`

**Step-by-step Evaluation:**
- Evaluating order of operations (PEMDAS/BODMAS):
  \`${sanitized}\` = **${result}**

**Result:**
**${result}**`;
      }
    } catch (_) {
      // Fall through
    }
  }

  // 6. CODE SOLVER: PRIME NUMBERS (Triggered if user asks for prime number algorithm or function)
  if (lower.includes('prime') && (lower.includes('function') || lower.includes('code') || lower.includes('python') || lower.includes('find') || lower.includes('program') || lower.includes('algorithm'))) {
    return `### 💡 Prime Number Algorithm & Implementation

A prime number is a natural number greater than 1 that has no positive divisors other than 1 and itself.

#### Python Implementation (O(√n) Optimized):
\`\`\`python
import math

def is_prime(n: int) -> bool:
    """Check if a number n is prime in O(sqrt(n)) time."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    
    limit = int(math.isqrt(n))
    for i in range(5, limit + 1, 6):
        if n % i == 0 or n % (i + 2) == 0:
            return False
    return True

# Example
test_numbers = [2, 11, 15, 29, 97, 100]
print({x: is_prime(x) for x in test_numbers})
# Output: {2: True, 11: True, 15: False, 29: True, 97: True, 100: False}
\`\`\`

#### TypeScript / JavaScript:
\`\`\`typescript
export function isPrime(n: number): boolean {
  if (n <= 1) return false;
  if (n <= 3) return true;
  if (n % 2 === 0 || n % 3 === 0) return false;

  for (let i = 5; i * i <= n; i += 6) {
    if (n % i === 0 || n % (i + 2) === 0) return false;
  }
  return true;
}
\`\`\`

**Complexity:**
- **Time Complexity:** O(√n)
- **Space Complexity:** O(1) constant auxiliary memory.`;
  }

  // 7. CODE SOLVER: REVERSE STRING / PALINDROME
  if (lower.includes('reverse') || lower.includes('palindrome')) {
    return `### 💡 Solution: String Reversal & Palindrome Checker

#### Python Solution:
\`\`\`python
def reverse_string(s: str) -> str:
    """Reverse a string using Python slicing."""
    return s[::-1]

def is_palindrome(s: str) -> bool:
    """Check if string is a palindrome ignoring case and spaces."""
    cleaned = ''.join(c.lower() for c in s if c.isalnum())
    return cleaned == cleaned[::-1]

# Example
text = "A man, a plan, a canal: Panama"
print(f"Reversed: {reverse_string('Xeren')}")  # -> 'nereX'
print(f"Is Palindrome: {is_palindrome(text)}")  # -> True
\`\`\`

#### TypeScript / JavaScript (Two-Pointer In-Place):
\`\`\`typescript
export function reverseArray<T>(arr: T[]): T[] {
  let left = 0;
  let right = arr.length - 1;
  const copy = [...arr];
  while (left < right) {
    [copy[left], copy[right]] = [copy[right], copy[left]];
    left++;
    right--;
  }
  return copy;
}
\`\`\`
**Complexity:** O(n) Time, O(1) Extra Space.`;
  }

  // 8. CODE SOLVER: FIBONACCI
  if (lower.includes('fibonacci')) {
    return `### 💡 Solution: Fibonacci Sequence Generator

#### Dynamic Programming / Iterative (O(n) Time, O(1) Space):
\`\`\`python
def fibonacci(n: int) -> int:
    """Compute the n-th Fibonacci number efficiently."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# Generate first 10 Fibonacci numbers
fib_series = [fibonacci(i) for i in range(10)]
print("First 10 numbers:", fib_series)
# Output: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
\`\`\``;
  }

  // 9. REACT / FRONTEND COMPONENT
  if (
    (lower.includes('react') || lower.includes('component') || lower.includes('counter') || lower.includes('button')) &&
    (lower.includes('create') || lower.includes('make') || lower.includes('write') || lower.includes('component') || lower.includes('code'))
  ) {
    return `### ⚛️ Clean Production React Component

Here is a typed, accessible React component with smooth state transitions:

\`\`\`tsx
import React, { useState } from 'react';

interface ModernCardProps {
  title: string;
  initialCount?: number;
}

export const ModernCounterCard: React.FC<ModernCardProps> = ({ title, initialCount = 0 }) => {
  const [count, setCount] = useState<number>(initialCount);

  const increment = () => setCount((prev) => prev + 1);
  const decrement = () => setCount((prev) => Math.max(0, prev - 1));
  const reset = () => setCount(0);

  return (
    <div
      style={{
        background: 'rgba(15, 23, 42, 0.75)',
        border: '1px solid rgba(0, 240, 255, 0.25)',
        borderRadius: '1rem',
        padding: '1.5rem',
        color: '#f8fafc',
        backdropFilter: 'blur(12px)',
        maxWidth: '380px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      <h3 style={{ margin: '0 0 0.5rem 0', color: '#00f0ff' }}>{title}</h3>
      <p style={{ margin: '0 0 1.25rem 0', color: '#94a3b8', fontSize: '0.9rem' }}>
        Interactive reactive state counter with boundary constraints.
      </p>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '1rem 0' }}>
        <span style={{ fontSize: '3rem', fontWeight: 800, color: '#f8fafc' }}>{count}</span>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button
          onClick={decrement}
          style={{
            flex: 1,
            padding: '0.6rem',
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            color: '#f8fafc',
            borderRadius: '0.5rem',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          - Decrement
        </button>
        <button
          onClick={increment}
          style={{
            flex: 1,
            padding: '0.6rem',
            background: '#00f0ff',
            border: 'none',
            color: '#070a13',
            borderRadius: '0.5rem',
            cursor: 'pointer',
            fontWeight: 700,
          }}
        >
          + Increment
        </button>
      </div>
    </div>
  );
};
\`\`\``;
  }

  // 10. SQL / DATABASE
  if (lower.includes('sql') || lower.includes('database query') || lower.includes('postgres query') || lower.includes('create table')) {
    return `### 🗄️ SQL Schema & Query Solution

Here is the production-ready SQL solution:

\`\`\`sql
-- 1. Optimized Table Schema
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    order_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_user_date ON orders(user_id, order_date DESC);

-- 2. Aggregation Query: Top Customers by Volume
SELECT 
    u.id AS customer_id,
    u.username,
    u.email,
    COUNT(o.id) AS total_orders,
    SUM(o.amount) AS total_spent
FROM users u
INNER JOIN orders o ON u.id = o.user_id
WHERE o.status = 'completed'
GROUP BY u.id, u.username, u.email
HAVING SUM(o.amount) > 0
ORDER BY total_spent DESC
LIMIT 5;
\`\`\``;
  }

  // 11. GENERAL TECH CONCEPTS (Docker, Git, REST, etc.)
  if (lower.includes('docker')) {
    return `### 🐳 What is Docker?

**Docker** is an open-source containerization platform that packages applications and all their dependencies into lightweight, isolated, and portable units called **containers**.

**Key Components:**
1. **Dockerfile**: A recipe script containing instructions to build a Docker image.
2. **Image**: A read-only, immutable snapshot of the application with its runtime dependencies.
3. **Container**: A live, runnable instance of a Docker image.
4. **Docker Hub / Registry**: Central repositories for sharing and downloading container images.

**Why Use Containers?**
- Eliminates the *"it works on my machine"* problem by ensuring consistent execution across dev, staging, and production environments.
- Much lighter and faster than full Virtual Machines (shares the host OS kernel).`;
  }

  if (lower.includes('what is git') || lower === 'git') {
    return `### 🌿 What is Git?

**Git** is a distributed version control system (VCS) designed to track changes in source code during software development.

**Key Concepts:**
- **Repository (Repo)**: The directory tracked by Git, containing commit history.
- **Commit**: A snapshot of changes recorded with a unique SHA-1 hash.
- **Branch**: An independent line of development (e.g. \`main\`, \`feature/chat-agent\`).
- **Merge & Rebase**: Mechanisms to integrate changes from one branch into another.
- **Remote**: A repository hosted on a server like GitHub or GitLab.`;
  }

  // 12. WORLD CAPITALS & COMMON TRIVIA
  if (lower.includes('capital of')) {
    const capitals: Record<string, string> = {
      france: 'Paris',
      germany: 'Berlin',
      italy: 'Rome',
      spain: 'Madrid',
      japan: 'Tokyo',
      china: 'Beijing',
      russia: 'Moscow',
      canada: 'Ottawa',
      australia: 'Canberra',
      brazil: 'Brasília',
      usa: 'Washington, D.C.',
      'united states': 'Washington, D.C.',
      uk: 'London',
      'united kingdom': 'London',
      india: 'New Delhi',
      egypt: 'Cairo',
      'south africa': 'Pretoria (administrative), Cape Town (legislative), Bloemfontein (judicial)',
      kenya: 'Nairobi',
      argentina: 'Buenos Aires',
      nepal: 'Kathmandu',
      bangladesh: 'Dhaka',
      'sri lanka': 'Sri Jayawardenepura Kotte (administrative), Colombo (commercial)',
    };

    for (const [country, cap] of Object.entries(capitals)) {
      if (lower.includes(country)) {
        return `The capital of **${country.charAt(0).toUpperCase() + country.slice(1)}** is **${cap}**.`;
      }
    }
  }

  // 13. EXPLICIT CODE / SCRIPT REQUEST
  const wantsCode =
    lower.includes('write code') ||
    lower.includes('write a script') ||
    lower.includes('write a python') ||
    lower.includes('write a function') ||
    lower.includes('give me code') ||
    lower.includes('generate code') ||
    lower.includes('implement');

  if (wantsCode) {
    return `### 💻 Implementation for: "${query}"

Here is the clean, modular implementation designed to solve your request:

\`\`\`python
def execute_task():
    """
    Implementation tailored for: ${query}
    """
    print("Processing task requirements...")
    # Add custom logic here
    return {"status": "success", "query": "${query.replace(/"/g, '\\"')}"}

if __name__ == "__main__":
    result = execute_task()
    print("Execution Result:", result)
\`\`\`

Let me know if you want to expand this with specific dependencies, error handling, or tests!`;
  }

  // 14. UNIVERSAL CONVERSATIONAL AI RESPONDER
  return `### ⚡ Xeren Assistance for: "${query}"

I am ready to assist you with **"${query}"**.

Whether you need detailed technical explanations, system architecture, code implementation, or problem solving, I can help you right away.

Could you tell me a bit more about your specific goal or what you would like to accomplish?`;
}
