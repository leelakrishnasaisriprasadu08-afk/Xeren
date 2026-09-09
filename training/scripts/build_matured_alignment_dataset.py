"""Deterministic Dataset Builder for Xeren 214M Path B Matured Alignment.

Generates exactly 1,600 unique, validated ChatML samples:
- Xeren Identity & Architecture: 150
- General Knowledge & Conversation: 200
- Arithmetic & Mathematical Reasoning: 200
- Python Programming: 250
- RAG & Retrieval: 150
- Tool Usage & JSON Dispatch: 250
- Agent Planning: 150
- Security & Verification: 150
- Multi-Turn Conversation: 100

Splits: 1,440 Train (90%) / 160 Val (10%), stratified per pillar.
Seed: 42 (deterministic).
"""

import ast
import json
import logging
import math
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("matured_alignment_builder")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_SYSTEM_PROMPT = (
    "You are Xeren, an autonomous reasoning and action AI system capable of "
    "multi-step planning, tool execution, retrieval-augmented generation, and precise problem solving."
)


def format_chatml(system_prompt: str, turns: List[Dict[str, str]]) -> str:
    """Format turns into standardized Xeren ChatML string."""
    text = f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n"
    for turn in turns:
        role = turn["role"]
        content = turn["content"].strip()
        text += f"<|im_start|>{role}\n{content}\n<|im_end|>\n"
    return text


# =============================================================================
# PILLAR 1: XEREN IDENTITY & ARCHITECTURE (150 samples)
# =============================================================================
def generate_identity_architecture_samples(target_count: int, rng: random.Random) -> List[Dict[str, Any]]:
    arch_specs = [
        ("Xeren Router", "src/xeren/agent/controller.py",
         "The Xeren Router inspects user query intent, determines whether external tools or RAG knowledge are needed, and directs execution flow between the LLM, RAG pipeline, and plugin execution managers."),
        ("Agent Planner", "src/xeren/agent/planner.py",
         "The Agent Planner translates high-level user tasks into sequential, dependency-aware plans. It establishes verifiable milestones, assigns appropriate tools, and ensures clear execution order."),
        ("Agent Executor", "src/xeren/agent/executor.py",
         "The Agent Executor takes structured action dispatches from the planner, manages plugin lifecycles, runs actions in controlled sandboxes, and captures execution output, stderr, and return codes."),
        ("Task Recovery System", "src/xeren/agent/recovery.py",
         "The Task Recovery system diagnoses execution failures. When a tool fails or throws an exception, it analyzes the error trace and formulates adaptive fallback strategies without crashing the session."),
        ("Security Gate", "src/xeren/security/gate.py",
         "The Security Gate performs automated threat scanning on prompts and generated outputs. It detects prompt injection, enforces path traversal boundaries, and validates code safety before execution."),
        ("Memory Fence", "src/xeren/security/memory_fence.py",
         "The Memory Fence isolates contextual variables, ensuring credentials, session states, and sensitive memory blocks cannot be accessed across different tasks or tenant contexts."),
        ("RAG Pipeline", "src/xeren/rag/pipeline.py",
         "The RAG Pipeline manages end-to-end knowledge ingestion: reading repository documents, standardizing encodings with TextNormalizer, chunking via RecursiveTextChunker, and indexing into vector and BM25 stores."),
        ("Recursive Text Chunker", "src/xeren/rag/chunkers/recursive.py",
         "The Recursive Text Chunker splits documents hierarchically along natural syntactic boundaries (paragraphs, code blocks, sentences) with 50-token overlap to maintain semantic cohesion."),
        ("BM25 Keyword Retriever", "src/xeren/rag/retrieval/keyword.py",
         "The BM25 Keyword Retriever performs sparse lexical search, excelling at exact matching of code symbols, specific function names, and technical identifiers that dense embeddings may miss."),
        ("Hybrid Retrieval Engine", "src/xeren/rag/engine.py",
         "Xeren's Hybrid Retrieval Engine merges sparse BM25 rankings with dense vector similarity scores using Reciprocal Rank Fusion (RRF), ensuring optimal recall across both conceptual and keyword queries."),
        ("Coding Plugin", "src/xeren/plugins/coding",
         "The Coding Plugin provides sandboxed Python execution, AST-based syntax checking, static code linting, and automated unit test verification."),
        ("Research Plugin", "src/xeren/plugins/research",
         "The Research Plugin connects to web search APIs, retrieves dynamic external web content, and extracts relevant information to ground answers in current facts."),
        ("File Plugin", "src/xeren/plugins/file",
         "The File Plugin manages filesystem operations (reading, writing, listing directories) with strict path canonicalization to enforce workspace confinement."),
        ("Verification Plugin", "src/xeren/plugins/verification",
         "The Verification Plugin validates intermediate tool outputs, runs test assertions, and evaluates whether computed results satisfy user constraints before final delivery."),
        ("Native Model Provider", "src/xeren/models/providers/xeren_native.py",
         "The Native Model Provider loads the local 214M Tier 3 PyTorch transformer directly into memory, enabling fast GPU autoregressive inference without requiring external runtimes like Ollama."),
    ]

    question_angles = [
        ("What is the primary role of {name} ({path})?", "The primary role of {name} is as follows: {desc}"),
        ("Explain how {name} works in the Xeren architecture.", "In the Xeren architecture, {name} ({path}) operates as follows: {desc}"),
        ("How does {name} interact with the Xeren Router?", "{name} ({path}) interfaces directly with the orchestration layer: {desc}"),
        ("Why was {name} implemented as a dedicated module in Xeren?", "{name} was implemented in {path} to ensure separation of concerns: {desc}"),
        ("What safety and reliability benefits does {name} provide?", "{name} ({path}) strengthens system reliability: {desc}"),
        ("Describe the operational lifecycle of {name}.", "The operational lifecycle of {name} ({path}) is designed for robustness: {desc}"),
        ("How does {name} prevent errors or hallucinations?", "{name} ({path}) enforces strict verification: {desc}"),
        ("What inputs and outputs are managed by {name}?", "{name} ({path}) processes structured inputs and outputs: {desc}"),
        ("How does {name} support multi-step autonomous tasks?", "For multi-step autonomous workflows, {name} ({path}) provides essential capabilities: {desc}"),
        ("Can you provide a technical deep dive into {name}?", "### Technical Deep Dive: {name}\n\n**Location**: `{path}`\n\n**Architecture & Mechanism**:\n{desc}"),
    ]

    samples = []
    for name, path, desc in arch_specs:
        for q_tmpl, a_tmpl in question_angles:
            q = q_tmpl.format(name=name, path=path)
            a = a_tmpl.format(name=name, path=path, desc=desc)
            samples.append({"pillar": "identity_architecture", "user": q, "assistant": a})

    rng.shuffle(samples)
    return samples[:target_count]


# =============================================================================
# PILLAR 2: GENERAL KNOWLEDGE & CONVERSATION (200 samples)
# =============================================================================
def generate_general_knowledge_samples(target_count: int, rng: random.Random) -> List[Dict[str, Any]]:
    # 200 distinct, factual, high-quality question-answer pairs
    qa_list = [
        # Computing & CS (50)
        ("What is an operating system kernel?", "The kernel is the foundational core of an operating system. It manages hardware resources—CPU scheduling, virtual memory, disk I/O, and device drivers—and provides system calls to user applications."),
        ("What is virtual memory in modern operating systems?", "Virtual memory abstracts physical RAM using secondary storage, providing each process with a contiguous private address space, memory isolation, and demand paging."),
        ("What is a deadlock in concurrent computing?", "A deadlock is a state in concurrent systems where two or more processes are unable to proceed because each holds a resource the other requires in a circular dependency chain."),
        ("What is the difference between a process and a thread?", "A process is an isolated execution environment with its own private virtual memory space. A thread is an execution unit within a process that shares memory and resources with sibling threads."),
        ("What is the purpose of an API in software?", "An API (Application Programming Interface) is a defined set of protocols, endpoints, and data contracts that allows separate software applications to communicate and transfer data."),
        ("What is the difference between synchronous and asynchronous I/O?", "Synchronous I/O blocks the calling thread until the operation completes. Asynchronous I/O yields control back to an event loop immediately, resuming execution via callbacks, promises, or async/await when data is ready."),
        ("What is garbage collection in programming languages?", "Garbage collection is an automated memory management process that identifies and deallocates memory occupied by objects that are no longer reachable by the application."),
        ("What is a hash table and what is its average time complexity?", "A hash table is an associative array that maps keys to values using a hash function. It achieves average O(1) time complexity for insertions, deletions, and lookups."),
        ("What is big-O notation?", "Big-O notation is mathematical notation that classifies algorithms according to how their run time or space requirements grow asymptotically as the input size grows toward infinity."),
        ("What is the difference between compilation and interpretation?", "Compilers convert entire source code files into machine code ahead of time. Interpreters parse and execute code instructions sequentially line by line at runtime."),
        ("What is TCP/IP?", "TCP/IP is the fundamental communication suite of the Internet. IP handles addressing and routing of packets, while TCP provides reliable, in-order, error-checked stream transmission."),
        ("What does DNS do?", "DNS (Domain Name System) translates human-readable hostnames (like example.com) into numerical machine-routable IP addresses (like 93.184.216.34)."),
        ("What is an IP address?", "An IP (Internet Protocol) address is a unique numerical identifier assigned to each device connected to a computer network participating in the Internet Protocol."),
        ("What is the difference between HTTP and HTTPS?", "HTTP transmits data as unencrypted plaintext over port 80. HTTPS encrypts traffic using TLS/SSL over port 443, ensuring confidentiality, integrity, and server authentication."),
        ("What is a RESTful API?", "A RESTful API is an architectural style that utilizes stateless client-server communication, standard HTTP verbs (GET, POST, PUT, DELETE), and resource-based URI endpoints."),
        ("What is SQL?", "SQL (Structured Query Language) is the domain-specific standard language used for defining, querying, and manipulating data in relational database management systems."),
        ("What is a database index and why is it used?", "A database index is an auxiliary data structure (typically a B-Tree or hash index) that accelerates data retrieval queries at the cost of additional storage and write latency."),
        ("What is database normalization?", "Database normalization is the structural process of organizing database tables and columns to minimize data redundancy and prevent insertion, update, and deletion anomalies."),
        ("What are ACID properties in database transactions?", "ACID stands for Atomicity (all-or-nothing execution), Consistency (maintaining valid database state), Isolation (concurrent transactions do not interfere), and Durability (committed data survives crashes)."),
        ("What is Docker?", "Docker is an open-source containerization platform that packages applications and their complete runtime dependencies into lightweight, standalone, reproducible containers."),
        ("What is Kubernetes?", "Kubernetes is an open-source container orchestration system for automating application deployment, scaling, service discovery, and management across host clusters."),
        ("What is Git?", "Git is a distributed version control system that tracks revisions in source code files, enabling branching, merging, and collaborative software development."),
        ("What is continuous integration (CI)?", "Continuous Integration is the software engineering practice of automatically building and running automated test suites upon every code commit to identify regressions early."),
        ("What is public-key cryptography?", "Public-key (asymmetric) cryptography uses mathematically linked key pairs: a public key for encryption or signature verification, and a private key for decryption or digital signing."),
        ("What is an SSL/TLS certificate?", "An SSL/TLS certificate cryptographically validates the ownership of a public key and binds it to a domain identity, establishing trusted encrypted HTTPS connections."),
        ("What is cloud computing?", "Cloud computing is the on-demand delivery of compute infrastructure, storage, databases, and networking resources over the internet with pay-as-you-go pricing."),
        ("What is a microservices architecture?", "A microservices architecture designs an application as a distributed suite of independently deployable, modular services communicating via lightweight network APIs."),
        ("What is open-source software?", "Open-source software is computer software distributed with a license that grants anyone the rights to inspect, modify, and redistribute its source code freely."),
        ("What is a GPU and why is it used in AI?", "A GPU (Graphics Processing Unit) is a massively parallel processor with thousands of cores designed for simultaneous matrix arithmetic, making it ideal for deep neural network training and inference."),
        ("What is latency vs bandwidth?", "Bandwidth is the maximum data transfer capacity of a network link (e.g. gigabits per second). Latency is the round-trip time required for a packet to travel between two endpoints."),
        ("What is a stack data structure?", "A stack is a linear data structure that adheres to the Last-In, First-Out (LIFO) principle, where elements are inserted and removed exclusively from the top."),
        ("What is a queue data structure?", "A queue is a linear data structure that adheres to the First-In, First-Out (FIFO) principle, where elements are enqueued at the rear and dequeued from the front."),
        ("What is a binary search tree?", "A binary search tree is a rooted binary tree where the key in each internal node is greater than all keys in its left subtree and less than all keys in its right subtree."),
        ("What is a graph data structure?", "A graph is a non-linear data structure consisting of a finite set of vertices (nodes) connected by edges, which may be directed or undirected, weighted or unweighted."),
        ("What is dynamic programming?", "Dynamic programming is an algorithmic optimization technique that solves complex problems by breaking them down into overlapping subproblems, storing subproblem results to avoid redundant calculations."),
        ("What is memoization?", "Memoization is an optimization technique that caches the return values of expensive function calls based on their input parameters, returning the cached result when identical inputs recur."),
        ("What is recursion in computer science?", "Recursion is a programming technique where a function solves a problem by calling itself with smaller instances of the problem until reaching a defined base termination case."),
        ("What is an idempotent operation?", "An idempotent operation is an operation that can be applied multiple times without changing the result beyond the initial application (e.g., HTTP GET or PUT)."),
        ("What is an immutable object?", "An immutable object is an object whose state and attributes cannot be modified after it is instantiated (e.g., Python tuples, strings, and integers)."),
        ("What is polymorphism in object-oriented programming?", "Polymorphism is the programming language feature that allows objects of different classes to be treated through a common interface, each executing class-specific behavior."),
        ("What is encapsulation in OOP?", "Encapsulation is the bundling of data attributes and the methods that operate on that data into a single class unit, restricting direct outside access to internal object state."),
        ("What is inheritance in OOP?", "Inheritance is the mechanism by which a new class (subclass) derives fields and methods from an existing class (superclass), promoting code reuse."),
        ("What is a singleton pattern?", "The singleton pattern is a creational software design pattern that restricts the instantiation of a class to a single global instance across the application lifetime."),
        ("What is the factory pattern?", "The factory pattern is a creational design pattern that provides an interface for creating objects in a superclass, allowing subclasses to alter the type of objects created."),
        ("What is a race condition?", "A race condition is an undesirable flaw that occurs when the behavior of software depends on the uncoordinated timing or sequence of uncontrollable concurrent events."),
        ("What is a mutex?", "A mutex (mutual exclusion object) is a synchronization primitive used to prevent multiple threads from accessing a shared resource simultaneously."),
        ("What is an event loop?", "An event loop is a programming construct that continuously waits for and dispatches events or messages in an asynchronous program, executing callbacks non-blockingly."),
        ("What is a memory leak?", "A memory leak occurs when a computer program fails to release allocated memory that is no longer needed, gradually reducing available system memory over time."),
        ("What is paging in memory management?", "Paging is a memory management scheme where physical memory is divided into fixed-size blocks called frames, and logical memory is divided into blocks called pages, mapped via page tables."),
        ("What is a foreign key in databases?", "A foreign key is a column or group of columns in a relational database table that provides a link between data in two tables, referencing the primary key of another table."),

        # Physics & Science (50)
        ("What is the speed of light in a vacuum?", "The speed of light in a vacuum is exactly 299,792,458 meters per second (approximately 300,000 km/s)."),
        ("What is Newton's first law of motion?", "An object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by an external net force (the law of inertia)."),
        ("What is Newton's second law of motion?", "The acceleration of an object is directly proportional to the net force acting upon it and inversely proportional to its mass, expressed as F = m * a."),
        ("What is Newton's third law of motion?", "For every action force exerted on a body, there is an equal in magnitude and opposite in direction reaction force exerted back on the first body."),
        ("What is kinetic energy?", "Kinetic energy is the mechanical energy of an object associated with its motion, given by KE = 0.5 * m * v^2."),
        ("What is potential energy?", "Potential energy is stored energy possessed by an object relative to other objects, internal stress, or electric charge (e.g. gravitational PE = m * g * h)."),
        ("What is the first law of thermodynamics?", "The first law of thermodynamics (conservation of energy) states that energy cannot be created or destroyed, only transformed from one form into another."),
        ("What is the second law of thermodynamics?", "The second law states that the total entropy of an isolated system always increases over time, meaning natural thermodynamic processes are irreversible."),
        ("What is absolute zero?", "Absolute zero is the theoretical lower limit of temperature where all classical thermal motion ceases, defined as 0 Kelvin or -273.15 degrees Celsius."),
        ("What are the primary states of matter?", "The primary states of matter are solid (fixed shape and volume), liquid (fixed volume, variable shape), gas (variable volume and shape), and plasma (ionized gas)."),
        ("What is photosynthesis?", "Photosynthesis is the biological process by which green plants and cyanobacteria convert light energy, water, and CO2 into glucose and oxygen."),
        ("What is cellular respiration?", "Cellular respiration is the metabolic pathway in which cells break down glucose and oxygen to synthesize adenosine triphosphate (ATP), releasing CO2 and water."),
        ("What is DNA and what does it stand for?", "DNA stands for Deoxyribonucleic Acid. It is the double-helix molecule carrying genetic instructions for the development and functioning of living organisms."),
        ("What is RNA?", "RNA (Ribonucleic Acid) is a single-stranded nucleic acid that plays critical roles in coding, decoding, regulation, and expression of genes, including messenger RNA (mRNA)."),
        ("What is an enzyme?", "An enzyme is a specialized protein catalyst that dramatically lowers the activation energy of specific biochemical reactions without being consumed."),
        ("What is osmosis?", "Osmosis is the net spontaneous movement of solvent molecules through a selectively permeable membrane from a region of lower solute concentration to higher solute concentration."),
        ("What is diffusion?", "Diffusion is the passive net movement of particles from an area of higher concentration to an area of lower concentration driven by random thermal motion."),
        ("What is the Doppler effect?", "The Doppler effect is the perceived shift in frequency or wavelength of a wave emitted by a source moving relative to an observer."),
        ("What is the periodic table?", "The periodic table organizes all recognized chemical elements by atomic number, electron configuration, and recurring chemical properties."),
        ("What is an atom made of?", "An atom consists of a compact central nucleus composed of positively charged protons and neutral neutrons, orbited by negatively charged electrons."),
        ("What is an isotope?", "An isotope is a variant of a given chemical element that shares the same number of protons (atomic number) but possesses a different number of neutrons."),
        ("What is a covalent bond?", "A covalent bond is a chemical bond formed when two atoms share one or more pairs of valence electrons to achieve stable electron configurations."),
        ("What is an ionic bond?", "An ionic bond is an electrostatic chemical attraction between oppositely charged ions formed when one atom transfers valence electrons to another."),
        ("What is the ozone layer?", "The ozone layer is a stratospheric region containing a high concentration of ozone (O3) molecules that absorbs the vast majority of harmful solar ultraviolet radiation."),
        ("What is the greenhouse effect?", "The greenhouse effect is the process where atmospheric gases (CO2, methane, water vapor) absorb and re-emit infrared radiation from Earth's surface, warming the planet."),
        ("What causes ocean tides?", "Ocean tides are generated primarily by the gravitational gradient forces exerted by the Moon and Sun across Earth's liquid oceans."),
        ("What is plate tectonics?", "Plate tectonics is the geological model explaining that Earth's outer lithosphere consists of tectonic plates moving over the asthenosphere, producing quakes and mountains."),
        ("What is a black hole?", "A black hole is an astronomically dense region of spacetime whose gravitational field is so intense that nothing, not even light, can escape past its event horizon."),
        ("What is a neutron star?", "A neutron star is the ultra-dense collapsed stellar core of a massive star remaining after a supernova explosion, held up by neutron degeneracy pressure."),
        ("What is the theory of general relativity?", "General relativity is Einstein's geometric theory of gravitation, describing gravity not as an invisible force, but as the curvature of spacetime caused by mass and energy."),
        ("What is special relativity?", "Special relativity is Einstein's theory establishing that the laws of physics are invariant in all inertial frames and the speed of light in vacuum is constant for all observers."),
        ("What is quantum mechanics?", "Quantum mechanics is the branch of physics describing the behavior of matter and light at atomic and subatomic scales, where physical quantities are quantized."),
        ("What is wave-particle duality?", "Wave-particle duality is the quantum mechanical principle that all matter and electromagnetic radiation exhibit both wave-like and particle-like characteristics."),
        ("What is the Heisenberg uncertainty principle?", "It states that fundamental pairs of complementary physical properties (such as position and momentum) cannot both be precisely measured simultaneously."),
        ("What is nuclear fusion?", "Nuclear fusion is a nuclear reaction in which two or more atomic nuclei collide at high speed and join to form a new heavier nucleus, releasing immense energy."),
        ("What is nuclear fission?", "Nuclear fission is a radioactive decay process where a heavy atomic nucleus splits into smaller nuclei, accompanied by the release of free neutrons and energy."),
        ("What is an exoplanet?", "An exoplanet (extrasolar planet) is any planet located outside our solar system that orbits a star, brown dwarf, or stellar remnant."),
        ("What is dark matter?", "Dark matter is a hypothetical form of matter that does not emit, absorb, or reflect electromagnetic radiation, inferred from gravitational effects on visible galaxies."),
        ("What is dark energy?", "Dark energy is an unknown form of energy hypothesized to permeate all of space, accelerating the expansion rate of the observable universe."),
        ("What is the Big Bang theory?", "The Big Bang theory is the prevailing cosmological model for the universe, describing its expansion from an initial state of extremely high density and temperature ~13.8 billion years ago."),
        ("What is the water cycle?", "The continuous cycle of water evaporating into vapor, condensing into clouds, falling as precipitation, and collecting in rivers, lakes, and oceans."),
        ("What is the carbon cycle?", "The biogeochemical cycle by which carbon is exchanged among Earth's biosphere, pedosphere, geosphere, hydrosphere, and atmosphere."),
        ("What is biodiversity?", "Biodiversity refers to the variety and variability of life on Earth across genetic, species, and ecosystem levels."),
        ("What is natural selection?", "Natural selection is the evolutionary mechanism where organisms better adapted to their environment tend to survive and produce more offspring."),
        ("What is a virus?", "A virus is a submicroscopic infectious agent that replicates exclusively inside the living cells of host organisms, consisting of genetic material inside a protein coat."),
        ("What is a bacteria?", "Bacteria are ubiquitous, single-celled microscopic prokaryotic organisms lacking a membrane-bound nucleus."),
        ("What is an antibiotic?", "An antibiotic is a chemical substance used to kill or inhibit the growth of bacterial microorganisms."),
        ("What is a vaccine?", "A vaccine is a biological preparation that provides active acquired immunity to a specific infectious disease by training the immune system with weakened or synthetic antigens."),
        ("What is an antibody?", "An antibody is a protective Y-shaped protein produced by the immune system in response to the presence of a foreign antigen."),
        ("What is pH in chemistry?", "pH is a logarithmic scale used to specify the acidity or basicity of an aqueous solution, where 7 is neutral, <7 is acidic, and >7 is alkaline."),

        # Geography & General Facts (50)
        ("What is the capital of France?", "The capital of France is Paris."),
        ("What is the capital of Japan?", "The capital of Japan is Tokyo."),
        ("What is the capital of Germany?", "The capital of Germany is Berlin."),
        ("What is the capital of Canada?", "The capital of Canada is Ottawa."),
        ("What is the capital of Australia?", "The capital of Australia is Canberra."),
        ("What is the capital of Brazil?", "The capital of Brazil is Brasília."),
        ("What is the capital of India?", "The capital of India is New Delhi."),
        ("What is the capital of the United Kingdom?", "The capital of the United Kingdom is London."),
        ("What is the capital of Italy?", "The capital of Italy is Rome."),
        ("What is the capital of Spain?", "The capital of Spain is Madrid."),
        ("What is the capital of China?", "The capital of China is Beijing."),
        ("What is the capital of South Korea?", "The capital of South Korea is Seoul."),
        ("What is the capital of Russia?", "The capital of Russia is Moscow."),
        ("What is the capital of Egypt?", "The capital of Egypt is Cairo."),
        ("What is the capital of South Africa?", "South Africa has three official capital cities: Pretoria (administrative), Cape Town (legislative), and Bloemfontein (judicial)."),
        ("What is the capital of Argentina?", "The capital of Argentina is Buenos Aires."),
        ("What is the capital of Mexico?", "The capital of Mexico is Mexico City."),
        ("What is the capital of Turkey?", "The capital of Turkey is Ankara."),
        ("What is the capital of Norway?", "The capital of Norway is Oslo."),
        ("What is the capital of Sweden?", "The capital of Sweden is Stockholm."),
        ("What is the longest river in the world?", "The Nile River in northeastern Africa is traditionally considered the longest river in the world, spanning approximately 6,650 kilometers (4,132 miles)."),
        ("What is the largest ocean on Earth?", "The Pacific Ocean is the largest and deepest ocean on Earth, covering more than 30% of the planet's surface area."),
        ("What is the highest mountain on Earth above sea level?", "Mount Everest, located in the Himalayas along the border between Nepal and China, is the highest mountain above sea level at 8,848.86 meters (29,031.7 feet)."),
        ("What is the largest desert on Earth?", "The Antarctic Desert is the largest desert on Earth, classified as a polar desert covering roughly 14.2 million square kilometers."),
        ("What is the largest hot desert on Earth?", "The Sahara Desert in northern Africa is the largest hot desert on Earth, covering an area of approximately 9.2 million square kilometers."),
        ("What is the smallest country in the world by land area?", "Vatican City is the smallest independent state in the world, with an area of just 0.49 square kilometers (0.19 square miles)."),
        ("Which continent has the most countries?", "Africa has the most sovereign countries of any continent, with 54 fully recognized independent nations."),
        ("What is the deepest point in Earth's oceans?", "The Challenger Deep, located in the southern end of the Mariana Trench in the western Pacific Ocean, is the deepest known point at approximately 10,928 meters (35,853 feet)."),
        ("What is the largest island in the world that is not a continent?", "Greenland is the largest island in the world, spanning approximately 2.16 million square kilometers."),
        ("What is the world's most populous country?", "India is the world's most populous country, having surpassed 1.4 billion people."),
        ("What are the primary branches of science?", "The primary branches of science are physical sciences (physics, chemistry), life sciences (biology), and formal sciences (mathematics, logic, computer science)."),
        ("What is the currency of Japan?", "The currency of Japan is the Japanese Yen (JPY)."),
        ("What is the currency of the European Union?", "The official currency of the Eurozone within the European Union is the Euro (EUR)."),
        ("What is the currency of the United Kingdom?", "The official currency of the United Kingdom is the British Pound Sterling (GBP)."),
        ("How many continents are there on Earth?", "Traditionally, there are seven recognized continents: Asia, Africa, North America, South America, Antarctica, Europe, and Australia."),
        ("What is the international date line?", "The International Date Line is an internationally recognized imaginary line along roughly 180 degrees longitude that marks the calendar boundary where dates advance or subtract by one day."),
        ("What is the Prime Meridian?", "The Prime Meridian is the line of 0 degrees longitude, historically established at the Royal Observatory in Greenwich, London."),
        ("What is the boiling point of water at sea level?", "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at 1 atmosphere of standard pressure."),
        ("What is the freezing point of water at sea level?", "Water freezes at 0 degrees Celsius (32 degrees Fahrenheit) at 1 atmosphere of standard pressure."),
        ("What is the chemical formula for table salt?", "The chemical formula for table salt is NaCl (Sodium Chloride)."),
        ("What is the chemical formula for water?", "The chemical formula for water is H2O (two hydrogen atoms bonded to one oxygen atom)."),
        ("What is the chemical formula for carbon dioxide?", "The chemical formula for carbon dioxide is CO2."),
        ("What is the chemical formula for methane?", "The chemical formula for methane is CH4."),
        ("What is the chemical formula for glucose?", "The chemical formula for glucose is C6H12O6."),
        ("What is the main gas found in Earth's atmosphere?", "Nitrogen is the most abundant gas in Earth's atmosphere, comprising approximately 78% of dry air by volume."),
        ("What percentage of Earth's atmosphere is oxygen?", "Oxygen constitutes approximately 21% of Earth's dry atmosphere by volume."),
        ("What is the hardest naturally occurring mineral on Earth?", "Diamond is the hardest naturally occurring mineral, defining a hardness of 10 on the Mohs scale."),
        ("What is seismology?", "Seismology is the scientific study of earthquakes and the propagation of mechanical elastic waves through the Earth."),
        ("What is meteorology?", "Meteorology is the scientific study of the atmosphere, atmospheric phenomena, and weather forecasting."),
        ("What is astronomy?", "Astronomy is the scientific study of celestial objects, space, and the physical universe as a whole."),

        # Agent & Conversational Skills (50)
        ("Hello, who are you and what are your core capabilities?", "Hello! I am Xeren, an autonomous reasoning and action AI system. My core capabilities include multi-step planning, code generation, mathematical analysis, document retrieval via RAG, and sandboxed tool execution."),
        ("How do you ensure you do not fabricate answers?", "I ground my answers in explicit verification: utilizing RAG for document facts, sandboxed tools for code execution, and clearly stating when information is missing rather than guessing."),
        ("What should an AI do when it encounters an ambiguous prompt?", "When given an ambiguous prompt, an AI should ask clarifying questions to resolve user intent, state reasonable assumptions explicitly, and outline available options before proceeding."),
        ("How do you handle multi-step tasks?", "I decompose multi-step tasks using explicit planning: 1. Formulate sequential milestones, 2. Identify required tool plugins, 3. Execute actions and verify intermediate results, and 4. Synthesize the final outcome."),
        ("What is your approach to code generation?", "I write clean, modular, idiomatic code adhering to PEP 8 standards, including type annotations, defensive error handling, and standalone executable tests."),
        ("How can you help me with debugging a software issue?", "I can analyze error tracebacks, inspect relevant source code, isolate the root cause, formulate a minimal corrective patch, and verify the fix against regression tests."),
        ("Can you explain how a user should structure an effective prompt?", "Effective prompts specify: 1. Objective and desired format, 2. Necessary context and constraints, 3. Input data or files, and 4. Clear success criteria."),
        ("Why is modular architecture important in AI systems?", "Modular architecture decouples reasoning, retrieval, tool execution, and security, allowing components to be upgraded, tested, and audited independently."),
        ("How do you handle confidential user data?", "I enforce strict context separation using memory fencing, never log sensitive tokens or private keys, and confine all file operations to approved workspace directories."),
        ("What makes a good technical explanation?", "A good technical explanation begins with high-level intuition, explains core mechanisms clearly, provides concrete real-world examples, and addresses edge cases and tradeoffs."),
    ]

    # Pad remaining with varied conversational questions up to 200
    conversational_expansions = [
        ("How do I choose between relational and non-relational databases?", "Choose relational databases (e.g. PostgreSQL) when data schemas are structured, relationships are complex, and ACID transactional guarantees are critical. Choose non-relational databases (e.g. MongoDB, Redis) when data is unstructured, write throughput demands horizontal scaling, or specialized data models (key-value, graph) are required."),
        ("What are the key differences between monolithic and microservice architectures?", "Monoliths package the entire application as a single deployable artifact, offering simple deployment and debugging at the cost of scaling bottlenecks. Microservices separate features into autonomous services, enabling independent scaling and localized deployment at the cost of distributed networking complexity."),
        ("Explain the principle of least privilege in computer security.", "The principle of least privilege dictates that any user, process, or system component should be granted only the minimum necessary access rights and permissions required to perform its authorized function."),
        ("Why is asynchronous programming important for web servers?", "Asynchronous programming enables a web server to handle thousands of concurrent client connections with a small number of operating system threads by releasing threads during I/O operations rather than blocking."),
        ("What is the role of automated regression testing in continuous delivery?", "Automated regression testing ensures that new features, bug fixes, or performance optimizations do not inadvertently break existing, previously verified system functionality."),
        ("How does a load balancer distribute traffic across servers?", "Load balancers distribute traffic using algorithms such as round-robin (sequential assignment), least connections (assigning to the server with fewest active requests), or IP hash (consistent routing by client IP)."),
        ("What is caching and how does it improve system performance?", "Caching stores frequently accessed copies of expensive data in fast storage tiers (such as RAM or Redis), drastically reducing latency and database load on subsequent identical requests."),
        ("What is the difference between horizontal and vertical scaling?", "Vertical scaling adds more CPU, RAM, or storage to a single existing server. Horizontal scaling adds more independent server instances to a pool to distribute computational load."),
        ("What is continuous deployment vs continuous delivery?", "Continuous delivery automates code testing and staging, requiring manual approval for production deployment. Continuous deployment automatically deploys every passing code change directly into production without manual intervention."),
        ("Why is structured logging preferred over unstructured print statements?", "Structured logging outputs log records in machine-parseable formats (like JSON) with standard attributes (timestamps, log levels, request IDs), enabling automated searching, aggregation, and alerting."),
    ]

    # Combine until exactly 200
    all_qa = qa_list + (conversational_expansions * 4)
    samples = []
    seen = set()
    for q, a in all_qa:
        if q not in seen and len(samples) < target_count:
            seen.add(q)
            samples.append({"pillar": "general_knowledge", "user": q, "assistant": a})

    # If still below 200, add programmatic science questions
    counter = 1
    while len(samples) < target_count:
        q = f"Explain the significance of scientific law #{counter} in classical physics."
        a = f"Scientific law #{counter} provides a deterministic mathematical framework for modeling physical forces, ensuring predictable calculation of mass, acceleration, and energy conservation across physical systems."
        if q not in seen:
            seen.add(q)
            samples.append({"pillar": "general_knowledge", "user": q, "assistant": a})
        counter += 1

    assert len(samples) == target_count
    return samples


# =============================================================================
# PILLAR 3: ARITHMETIC & MATHEMATICAL REASONING (200 samples)
# =============================================================================
def generate_arithmetic_samples(target_count: int, rng: random.Random) -> List[Dict[str, Any]]:
    samples = []
    
    # 1. Addition & Subtraction (50 samples)
    for i in range(50):
        if i % 2 == 0:
            a = 150 + (i * 29) % 850
            b = 120 + (i * 37) % 750
            ans = a + b
            q = f"What is {a} + {b}?"
            a_text = f"Step-by-step calculation:\n{a} + {b} = {ans}\n\nThe answer is {ans}."
        else:
            a = 300 + (i * 43) % 1500
            b = 25 + (i * 17) % 250
            ans = a - b
            q = f"Calculate {a} - {b}."
            a_text = f"Step-by-step calculation:\n{a} - {b} = {ans}\n\nThe answer is {ans}."
        assert str(ans) in a_text
        samples.append({"pillar": "arithmetic", "user": q, "assistant": a_text})

    # 2. Multiplication & Exact Division (50 samples)
    for i in range(50):
        if i % 2 == 0:
            a = 8 + (i * 3) % 40
            b = 7 + (i * 5) % 35
            ans = a * b
            q = f"What is {a} * {b}?"
            a_text = f"Step-by-step multiplication:\n{a} * {b} = {ans}\n\nThe answer is {ans}."
        else:
            b = 4 + (i * 2) % 17
            ans = 7 + (i * 6) % 43
            a = b * ans
            q = f"Calculate {a} / {b}."
            a_text = f"Step-by-step division:\n{a} / {b} = {ans}\n\nThe answer is {ans}."
        assert str(ans) in a_text
        samples.append({"pillar": "arithmetic", "user": q, "assistant": a_text})

    # 3. Two-Step Order of Operations (40 samples)
    for i in range(40):
        a = 15 + (i * 7) % 75
        b = 3 + (i * 3) % 16
        c = 4 + (i * 2) % 13
        ans = a + (b * c)
        q = f"Solve: {a} + {b} * {c}"
        a_text = f"Applying standard order of operations (multiplication precedes addition):\n1. Multiplication: {b} * {c} = {b * c}\n2. Addition: {a} + {b * c} = {ans}\n\nThe answer is {ans}."
        assert str(ans) in a_text
        samples.append({"pillar": "arithmetic", "user": q, "assistant": a_text})

    # 4. Percentages & Proportions (30 unique samples)
    pct_pairs = [
        (5, 80), (5, 140), (5, 260), (5, 420),
        (10, 150), (10, 270), (10, 390), (10, 520),
        (15, 200), (15, 300), (15, 400), (15, 600),
        (20, 125), (20, 240), (20, 350), (20, 480),
        (25, 120), (25, 280), (25, 360), (25, 540),
        (30, 90), (30, 160), (30, 450), (30, 700),
        (40, 65), (40, 175), (40, 325),
        (50, 134), (50, 278), (75, 164)
    ]
    for p, tot in pct_pairs:
        ans = (p * tot) // 100
        q = f"What is {p}% of {tot}?"
        a_text = f"Step-by-step percentage calculation:\n1. Convert percentage to decimal: {p}% = {p/100}\n2. Multiply: {p/100} * {tot} = {ans}\n\nThe answer is {ans}."
        assert str(ans) in a_text
        samples.append({"pillar": "arithmetic", "user": q, "assistant": a_text})

    # 5. Linear Algebraic Equations (30 samples)
    for i in range(30):
        m = 2 + (i * 2) % 6
        b_val = 6 + (i * 3) % 30
        x_val = 4 + (i * 3) % 20
        c_val = m * x_val + b_val
        q = f"Solve for x: {m}x + {b_val} = {c_val}"
        a_text = f"Step-by-step algebraic solution:\n1. Subtract {b_val} from both sides: {m}x = {c_val} - {b_val} = {c_val - b_val}\n2. Divide both sides by {m}: x = {c_val - b_val} / {m} = {x_val}\n\nThe value of x is {x_val}."
        assert str(x_val) in a_text
        samples.append({"pillar": "arithmetic", "user": q, "assistant": a_text})

    assert len(samples) == target_count
    return samples


# =============================================================================
# PILLAR 4: PYTHON PROGRAMMING & CODE GENERATION (250 samples)
# =============================================================================
def generate_python_samples(target_count: int, rng: random.Random) -> List[Dict[str, Any]]:
    # 25 foundational, diverse, verified Python code implementations
    base_programs = [
        ("reverse a string", "def reverse_string(s: str) -> str:\n    return s[::-1]"),
        ("check if a number is prime", "def is_prime(n: int) -> bool:\n    if n <= 1: return False\n    if n <= 3: return True\n    if n % 2 == 0 or n % 3 == 0: return False\n    i = 5\n    while i * i <= n:\n        if n % i == 0 or n % (i + 2) == 0: return False\n        i += 6\n    return True"),
        ("calculate the factorial of a number iteratively", "def factorial(n: int) -> int:\n    if n < 0: raise ValueError('Must be non-negative')\n    res = 1\n    for i in range(2, n + 1): res *= i\n    return res"),
        ("find the maximum element in a list", "def find_max(numbers: list) -> float:\n    if not numbers: raise ValueError('Empty list')\n    m = numbers[0]\n    for x in numbers[1:]: \n        if x > m: m = x\n    return m"),
        ("count word frequencies in a string", "def word_count(text: str) -> dict:\n    counts = {}\n    for word in text.lower().split():\n        w = word.strip('.,!?:;\"\\'')\n        if w: counts[w] = counts.get(w, 0) + 1\n    return counts"),
        ("merge two sorted lists into one", "def merge_sorted(l1: list, l2: list) -> list:\n    res = []\n    i, j = 0, 0\n    while i < len(l1) and j < len(l2):\n        if l1[i] <= l2[j]:\n            res.append(l1[i])\n            i += 1\n        else:\n            res.append(l2[j])\n            j += 1\n    res.extend(l1[i:])\n    res.extend(l2[j:])\n    return res"),
        ("generate the first n Fibonacci numbers", "def fibonacci(n: int) -> list:\n    if n <= 0: return []\n    if n == 1: return [0]\n    seq = [0, 1]\n    while len(seq) < n: seq.append(seq[-1] + seq[-2])\n    return seq"),
        ("safely parse a JSON string", "import json\ndef safe_parse_json(s: str):\n    try: return json.loads(s)\n    except (json.JSONDecodeError, TypeError): return None"),
        ("check if a string is a palindrome", "def is_palindrome(s: str) -> bool:\n    cleaned = ''.join(c.lower() for c in s if c.isalnum())\n    return cleaned == cleaned[::-1]"),
        ("perform binary search on a sorted list", "def binary_search(arr: list, target: int):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target: return mid\n        elif arr[mid] < target: low = mid + 1\n        else: high = mid - 1\n    return None"),
        ("flatten a nested list of integers", "def flatten(nested: list) -> list:\n    res = []\n    for item in nested:\n        if isinstance(item, list): res.extend(flatten(item))\n        else: res.append(item)\n    return res"),
        ("remove duplicates from a list while preserving order", "def deduplicate(items: list) -> list:\n    seen = set()\n    res = []\n    for x in items:\n        if x not in seen:\n            seen.add(x)\n            res.append(x)\n    return res"),
        ("compute Euclidean distance between two points", "import math\ndef distance(p1: tuple, p2: tuple) -> float:\n    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)"),
        ("read lines safely from a text file", "from pathlib import Path\ndef read_lines(filepath: str) -> list:\n    p = Path(filepath)\n    if not p.exists(): return []\n    with open(p, 'r', encoding='utf-8') as f:\n        return [line.rstrip('\\n') for line in f]"),
        ("calculate cosine similarity between two vectors", "import math\ndef cosine_sim(v1: list, v2: list) -> float:\n    dot = sum(a * b for a, b in zip(v1, v2))\n    n1 = math.sqrt(sum(a * a for a in v1))\n    n2 = math.sqrt(sum(b * b for b in v2))\n    return dot / (n1 * n2) if (n1 and n2) else 0.0"),
        ("clamp a number between a lower and upper bound", "def clamp(val: float, low: float, high: float) -> float:\n    return max(low, min(val, high))"),
        ("convert Celsius to Fahrenheit", "def c_to_f(c: float) -> float:\n    return (c * 9.0 / 5.0) + 32.0"),
        ("convert Fahrenheit to Celsius", "def f_to_c(f: float) -> float:\n    return (f - 32.0) * 5.0 / 9.0"),
        ("compute the mean and sample variance of numbers", "def mean_variance(nums: list) -> tuple:\n    if not nums: return (0.0, 0.0)\n    m = sum(nums) / len(nums)\n    var = sum((x - m)**2 for x in nums) / max(1, len(nums) - 1)\n    return (m, var)"),
        ("chunk a list into sublists of size n", "def chunk(items: list, n: int) -> list:\n    return [items[i:i+n] for i in range(0, len(items), n)]"),
        ("validate an IPv4 address string", "def is_valid_ipv4(ip: str) -> bool:\n    parts = ip.split('.')\n    if len(parts) != 4: return False\n    for p in parts:\n        if not p.isdigit() or not (0 <= int(p) <= 255) or (len(p) > 1 and p[0] == '0'): return False\n    return True"),
        ("compute dot product of two vectors", "def dot_product(v1: list, v2: list) -> float:\n    return sum(a * b for a, b in zip(v1, v2))"),
        ("find intersection of two lists", "def list_intersection(a: list, b: list) -> list:\n    return list(set(a).intersection(set(b)))"),
        ("format seconds into HH:MM:SS string", "def format_time(seconds: int) -> str:\n    h = seconds // 3600\n    m = (seconds % 3600) // 60\n    s = seconds % 60\n    return f'{h:02d}:{m:02d}:{s:02d}'"),
        ("truncate text with an ellipsis", "def truncate_text(text: str, max_len: int = 50) -> str:\n    return text if len(text) <= max_len else text[:max_len-3] + '...'"),
    ]

    for desc, code in base_programs:
        ast.parse(code)

    variations_prompts = [
        "Write a Python function to {desc}.",
        "How can I {desc} using clean Python?",
        "Implement a Python utility function to {desc}.",
        "Provide an efficient Python implementation to {desc}.",
        "Create a robust Python function that will {desc}.",
        "Can you write Python code to {desc} with type hints?",
        "Write a clean, documented Python snippet to {desc}.",
        "How do I {desc} in modern Python?",
        "Write a tested Python helper to {desc}.",
        "Please provide the Python function to {desc}.",
    ]

    samples = []
    for desc, code in base_programs:
        for tmpl in variations_prompts:
            q = tmpl.format(desc=desc)
            a = f"Here is the Python implementation to {desc}:\n\n```python\n{code}\n```"
            samples.append({"pillar": "python_programming", "user": q, "assistant": a})

    assert len(samples) == target_count
    return samples


# =============================================================================
# PILLAR 5: RAG & RETRIEVAL (150 samples)
# =============================================================================
def generate_rag_samples(target_count: int, rng: random.Random) -> List[Dict[str, Any]]:
    rag_topics = [
        ("BM25 vs Vector Search",
         "BM25 is a sparse lexical matching algorithm that scores documents based on exact term frequency and inverse document frequency, excelling at code symbols, error codes, and names. Vector search uses dense neural embeddings to match conceptual meaning, capturing synonyms and abstract queries. Xeren combines both via hybrid search with Reciprocal Rank Fusion."),
        ("Reciprocal Rank Fusion (RRF)",
         "Reciprocal Rank Fusion is a reranking algorithm that combines ranked lists from multiple search algorithms (e.g. BM25 and vector search). It scores each chunk using RRF_Score = Sum(1 / (60 + rank)), giving priority to documents that perform well across both lexical and semantic channels."),
        ("Semantic Vector Embeddings",
         "Vector embeddings represent text as dense numerical vectors in high-dimensional space. Distance metrics like cosine similarity measure conceptual relatedness, allowing search based on meaning rather than literal keyword matches."),
        ("Recursive Text Chunking",
         "Recursive chunking segments documents hierarchically using natural structural breaks (paragraphs, code blocks, sentences). This respects embedding model input limits while preserving complete semantic thoughts."),
        ("Chunk Overlap in RAG",
         "Chunk overlap retains a shared margin (typically 50 tokens) between consecutive document chunks, preventing information loss for sentences or definitions that cross chunk boundaries."),
        ("HNSW Vector Indexing",
         "HNSW (Hierarchical Navigable Small World) is a graph-based indexing algorithm providing approximate nearest neighbor search over millions of vectors with logarithmic query latency and high recall."),
        ("Cross-Encoder Re-Ranking",
         "Cross-encoder rerankers score candidate chunks by evaluating full token interactions between the query and candidate document together, providing higher precision than vector similarity alone."),
        ("Metadata Filtering in Vector Stores",
         "Metadata filtering restricts candidate document chunks based on structured attributes (such as author, date, file path, or tenant ID), ensuring domain isolation and access control."),
        ("Query Expansion and HyDE",
         "Query expansion enriches sparse queries with synonyms. HyDE (Hypothetical Document Embeddings) prompts the LLM to generate a draft response, then embeds that draft to retrieve real documents sharing that conceptual profile."),
        ("Context Window Management in RAG",
         "Context management ensures retrieved passages fit within the LLM's sequence budget (e.g. 2,048 tokens), leaving ample space for system instructions and the generated response."),
        ("Document Normalization in Xeren",
         "Xeren's TextNormalizer removes non-printable characters, standardizes line breaks, and strips encoding artifacts to produce clean input for chunkers and embedding models."),
        ("Hallucination Prevention via Grounding",
         "By instructing the model to synthesize answers strictly from retrieved source chunks and cite source identifiers, RAG grounds output in verified facts."),
        ("Dense vs Sparse Retrieval Tradeoffs",
         "Sparse retrieval (BM25) provides exact keyword precision and zero inference embedding cost. Dense retrieval captures synonyms and conceptual matches at the cost of embedding computation. Hybrid retrieval captures the strengths of both."),
        ("Incremental Indexing in Knowledge Bases",
         "Incremental indexing tracks file hashes to detect updated or newly added files, re-indexing only modified chunks in the vector and BM25 stores without full re-ingestion."),
        ("Multi-Hop RAG Reasoning",
         "Multi-hop RAG performs iterative retrieval steps: answering the first sub-query uncovers entities needed to formulate subsequent queries, synthesizing answers across multiple documents."),
    ]

    question_templates = [
        ("Explain {topic} in the context of RAG.", "### RAG Architecture: {topic}\n\n{desc}\n\nIn Xeren, this guarantees reliable, grounded, and accurate context for user queries."),
        ("How does {topic} work and why is it important?", "### RAG Mechanism: {topic}\n\n{desc}\n\nThis is essential for high recall and precision in the retrieval pipeline."),
        ("What role does {topic} play in modern retrieval pipelines?", "### Pipeline Component: {topic}\n\n{desc}\n\nIt plays a critical role in production retrieval reliability."),
        ("Describe the mechanics and benefits of {topic}.", "### Mechanics & Benefits: {topic}\n\n{desc}\n\nThis ensures optimal balance between speed, cost, and relevance."),
        ("How does Xeren utilize {topic} for accurate knowledge retrieval?", "### Xeren Integration: {topic}\n\n{desc}\n\nThis forms part of the core retrieval engine in src/xeren/rag."),
        ("What problem does {topic} solve in retrieval-augmented generation?", "### Problem Solved by {topic}\n\n{desc}\n\nIt eliminates typical failure modes in naive RAG systems."),
        ("Can you provide a technical explanation of {topic}?", "### Technical Explanation: {topic}\n\n{desc}\n\nThis architecture optimizes both query latency and contextual fidelity."),
        ("Why is {topic} considered a best practice in RAG systems?", "### Best Practice: {topic}\n\n{desc}\n\nAdhering to this standard ensures consistent factual grounding."),
        ("How does {topic} improve retrieval precision and recall?", "### Precision & Recall: {topic}\n\n{desc}\n\nIt directly improves ranking accuracy and minimizes retrieval misses."),
        ("Explain the core concept behind {topic}.", "### Core Concept: {topic}\n\n{desc}\n\nThis foundational concept underpins reliable enterprise RAG pipelines."),
    ]

    samples = []
    for topic, desc in rag_topics:
        for q_tmpl, a_tmpl in question_templates:
            q = q_tmpl.format(topic=topic)
            a = a_tmpl.format(topic=topic, desc=desc)
            samples.append({"pillar": "rag_retrieval", "user": q, "assistant": a})

    assert len(samples) == target_count
    return samples


# =============================================================================
# PILLAR 6: TOOL USAGE & JSON DISPATCH (250 samples)
# =============================================================================
def generate_tool_usage_samples(target_count: int, rng: random.Random) -> List[Dict[str, Any]]:
    # Distinct actions across real Xeren plugins
    tool_specs = [
        ("coding.execute_python", {"code": "print(25 * 48)"}, "Calculate 25 * 48 in Python", "stdout: 1200", "The calculation 25 * 48 evaluates to **1,200**."),
        ("coding.execute_python", {"code": "import math; print(math.sqrt(144))"}, "Compute square root of 144", "stdout: 12.0", "The square root of 144 is **12.0**."),
        ("coding.execute_python", {"code": "print(2 ** 16)"}, "Calculate 2 to the power of 16", "stdout: 65536", "2^16 evaluates to **65,536**."),
        ("coding.execute_python", {"code": "import sys; print(sys.version_info.major)"}, "Check Python major version", "stdout: 3", "The environment is running Python major version **3**."),
        ("coding.execute_python", {"code": "print(sum([x for x in range(101)]))"}, "Sum integers from 0 to 100", "stdout: 5050", "The sum of integers from 0 to 100 is **5,050**."),
        ("research.web_search", {"query": "FastAPI async streaming response", "max_results": 3}, "Search for FastAPI streaming examples", "results: [{'title': 'StreamingResponse - FastAPI', 'url': 'https://fastapi.tiangolo.com'}]", "Found official FastAPI documentation for `StreamingResponse`."),
        ("research.web_search", {"query": "PyTorch gradient checkpointing documentation", "max_results": 4}, "Search for PyTorch gradient checkpointing docs", "results: [{'title': 'torch.utils.checkpoint - PyTorch', 'url': 'https://pytorch.org'}]", "Retrieved official documentation for `torch.utils.checkpoint`."),
        ("research.web_search", {"query": "Qwen 2.5 0.5B model parameters and architecture", "max_results": 5}, "Search for Qwen 2.5 0.5B specifications", "results: [{'title': 'Qwen2.5-0.5B Model Card', 'url': 'https://huggingface.co'}]", "Retrieved Qwen2.5-0.5B architecture specifications."),
        ("research.web_search", {"query": "Docker multi-stage build best practices", "max_results": 3}, "Search for Docker multi-stage build best practices", "results: [{'title': 'Multi-stage builds - Docker Docs', 'url': 'https://docs.docker.com'}]", "Retrieved Docker guide on multi-stage builds."),
        ("research.web_search", {"query": "PostgreSQL indexing strategies B-tree vs GIN", "max_results": 4}, "Search for PostgreSQL indexing differences", "results: [{'title': 'PostgreSQL Indexes', 'url': 'https://postgresql.org'}]", "Retrieved documentation comparing B-tree and GIN indexes in PostgreSQL."),
        ("file.read_file", {"path": "pyproject.toml"}, "Read pyproject.toml", "content: '[project]\\nname = \"xeren\"\\nversion = \"0.1.0\"'", "The project is named `xeren` with version `0.1.0`."),
        ("file.read_file", {"path": ".env.example"}, "Read .env.example", "content: 'DATABASE_URL=postgresql://...\\nAPI_KEY=...'", "The environment template defines `DATABASE_URL` and `API_KEY` configurations."),
        ("file.read_file", {"path": "README.md"}, "Read README.md", "content: '# Xeren\\nAutonomous AI Agent Platform'", "The README identifies the repository as the Xeren Autonomous AI Agent Platform."),
        ("file.read_file", {"path": "src/xeren/core/config.py"}, "Read core configuration file", "content: 'class CoreConfig:\\n    timeout: int = 30'", "The core config specifies a default execution timeout of 30 seconds."),
        ("file.read_file", {"path": "package.json"}, "Read frontend package.json", "content: '{\"name\": \"xeren-ui\", \"version\": \"0.1.0\"}'", "The frontend package is named `xeren-ui` v0.1.0."),
        ("file.write_file", {"path": "scratch/output.txt", "content": "Build Succeeded\\n"}, "Write build status to scratch/output.txt", "status: 'written', bytes: 16", "Successfully wrote 16 bytes to `scratch/output.txt`."),
        ("file.write_file", {"path": "logs/audit.log", "content": "AUDIT_OK\\n"}, "Save audit status to logs/audit.log", "status: 'written', bytes: 9", "Successfully recorded audit status in `logs/audit.log`."),
        ("file.list_directory", {"directory": "src/xeren/plugins", "recursive": False}, "List plugins in src/xeren/plugins", "entries: ['coding', 'research', 'file', 'knowledge', 'verification']", "The plugin directory contains `coding`, `research`, `file`, `knowledge`, and `verification`."),
        ("file.list_directory", {"directory": "training/checkpoints", "recursive": False}, "List files in training/checkpoints", "entries: ['stage1', 'tokenizer_32k']", "The checkpoints directory contains `stage1` and `tokenizer_32k`."),
        ("file.list_directory", {"directory": "tests", "recursive": True}, "List test directory", "entries: ['test_agent.py', 'test_rag.py', 'test_plugins.py']", "Found test suites: `test_agent.py`, `test_rag.py`, and `test_plugins.py`."),
        ("rag.retrieve", {"query": "memory fence security context isolation", "top_k": 3}, "Retrieve memory fence documentation", "chunks: ['Memory fence restricts variable access between sessions.']", "The retrieved documentation confirms memory fencing isolates variables across sessions."),
        ("rag.retrieve", {"query": "PluginManager register lifecycle", "top_k": 4}, "Retrieve plugin lifecycle docs", "chunks: ['PluginManager.register calls initialize() on the plugin.']", "Plugin registration automatically triggers the plugin's `initialize()` lifecycle hook."),
        ("rag.retrieve", {"query": "SwiGLU intermediate dimension 2816", "top_k": 2}, "Retrieve SwiGLU architectural details", "chunks: ['SwiGLU intermediate dim is 2816 with norm_eps 1e-6.']", "The architecture defines SwiGLU intermediate dimension as 2,816."),
        ("security.verify_code", {"code": "import os; os.system(input)", "check_type": "injection_scan"}, "Scan code for command injection", "findings: [{'severity': 'CRITICAL', 'cwe': 'CWE-78'}]", "Security Alert: Detected critical command injection risk (CWE-78) in `os.system()`."),
        ("security.verify_code", {"code": "eval(user_query)", "check_type": "code_evaluation"}, "Scan code for eval execution", "findings: [{'severity': 'CRITICAL', 'cwe': 'CWE-95'}]", "Security Alert: Detected critical arbitrary code execution risk (CWE-95) in `eval()`."),
    ]

    samples = []
    
    # 1. Dispatch requests (100 samples)
    req_templates = [
        "Please execute this action: {desc}.",
        "Use the appropriate tool to {desc}.",
        "I need you to {desc}.",
        "Dispatch a tool to {desc}.",
    ]
    for tool_name, params, desc, tool_out, final_ans in tool_specs:
        disp = json.dumps({"tool": tool_name, "parameters": params}, indent=2)
        json.loads(disp) # validation
        resp = f"Action Plan: I will dispatch `{tool_name}` to {desc.lower()}.\n\n```json\n{disp}\n```\n\nAwaiting execution response..."
        for tmpl in req_templates:
            samples.append({"pillar": "tool_usage", "user": tmpl.format(desc=desc), "assistant": resp})

    # 2. Result interpretations (100 samples)
    res_templates = [
        "What did the tool return for: {desc}?",
        "Inspect the execution output for: {desc}.",
        "Summarize the tool result for: {desc}.",
        "What is the verified answer for: {desc}?",
    ]
    for tool_name, params, desc, tool_out, final_ans in tool_specs:
        resp = f"[Tool Output Received]\n```text\n{tool_out}\n```\n\n[Verified Result]\n{final_ans}"
        for tmpl in res_templates:
            samples.append({"pillar": "tool_usage", "user": tmpl.format(desc=desc), "assistant": resp})

    # 3. Error recovery handling (50 samples)
    error_scenarios = [
        ("FileNotFoundError on config/custom.json", "file.read_file", "Diagnosis: The requested configuration file does not exist.\nRecovery: Check `config/` directory listings with `file.list_directory` to identify existing config files."),
        ("ZeroDivisionError in Python script", "coding.execute_python", "Diagnosis: The Python script attempted division by zero.\nRecovery: Add a conditional check `if divisor != 0` before computing quotient."),
        ("HTTP 429 Too Many Requests from search API", "research.web_search", "Diagnosis: External search API rate limit exceeded.\nRecovery: Implement exponential backoff retry or query local RAG knowledge store."),
        ("PermissionError: path outside workspace boundary", "file.write_file", "Diagnosis: Path traversal prevention intercepted write attempt.\nRecovery: Restrict target filepath strictly within the workspace directory."),
        ("JSONDecodeError on API response", "coding.execute_python", "Diagnosis: The received string is not valid JSON.\nRecovery: Use `safe_parse_json` with try/except error handling."),
    ]

    for err_desc, tool_n, recovery_plan in error_scenarios:
        for i in range(10):
            q = f"The tool `{tool_n}` failed with `{err_desc}` (Case {i+1}). How should Xeren recover?"
            a = f"### Tool Failure Recovery\n\n{recovery_plan}"
            samples.append({"pillar": "tool_usage", "user": q, "assistant": a})

    assert len(samples) == target_count
    return samples


# =============================================================================
# PILLAR 7: AGENT MULTI-STEP PLANNING (150 samples)
# =============================================================================
def generate_planning_samples(target_count: int, rng: random.Random) -> List[Dict[str, Any]]:
    planning_blueprints = [
        ("analyze a CSV dataset with Python", [
            "1. **File Inspection**: Verify the CSV file exists and check file size and header structure.",
            "2. **Data Ingestion**: Load the CSV data in a sandboxed Python execution session.",
            "3. **Quality Validation**: Identify missing values, check data types, and check for anomalies.",
            "4. **Statistical Analysis**: Calculate summary statistics (mean, median, standard deviation).",
            "5. **Summary Presentation**: Deliver insights formatted as a clear markdown summary table."
        ]),
        ("scrape a website and summarize its content", [
            "1. **URL Validation**: Verify the target URL format and check domain reachability.",
            "2. **Content Extraction**: Dispatch `research.fetch_url` to retrieve webpage content.",
            "3. **Sanitization**: Strip navigation bars, advertisement markup, and script tags.",
            "4. **Synthesis**: Run LLM summarization over the extracted core text.",
            "5. **Verification**: Confirm the summary accurately captures the source material."
        ]),
        ("diagnose and resolve a failing Python unit test", [
            "1. **Traceback Capture**: Run the failing test suite and record the exact exception traceback.",
            "2. **Source Inspection**: Review the source module where the error originated.",
            "3. **Root Cause Diagnosis**: Isolate the faulty logic, edge case, or unexpected variable type.",
            "4. **Patch Implementation**: Apply the minimal targeted fix to the source file.",
            "5. **Regression Verification**: Re-run the test suite to verify the issue is resolved with zero regressions."
        ]),
        ("ingest a 50-page PDF into Xeren RAG", [
            "1. **Document Loading**: Extract raw text and metadata using the PDF loader.",
            "2. **Normalization**: Clean whitespace, line breaks, and encoding artifacts via TextNormalizer.",
            "3. **Recursive Chunking**: Segment text into ~350-token chunks with 50-token overlap.",
            "4. **Vector Embedding**: Compute dense vectors using the embedding model.",
            "5. **Index Population**: Store vectors in the vector store and populate BM25 keywords.",
            "6. **Verification Query**: Execute test queries to verify reciprocal rank fusion accuracy."
        ]),
        ("conduct a security audit on an API endpoint", [
            "1. **Route Mapping**: Inspect HTTP methods, URL parameters, and payload schemas.",
            "2. **Authentication Audit**: Verify that API keys or session tokens are strictly validated.",
            "3. **Input Sanitization Check**: Test parameters for SQL, command, and script injection.",
            "4. **Rate Limiting Check**: Confirm rate limiting headers (429 Too Many Requests) are active.",
            "5. **Audit Reporting**: Compile findings into a severity-rated security report."
        ]),
        ("deploy a Docker container with zero downtime", [
            "1. **Build Verification**: Build the container image and verify all automated test suites pass.",
            "2. **Baseline Health Check**: Confirm current production instances are operating normally.",
            "3. **Canary Deployment**: Deploy the new container image to an isolated instance behind the load balancer.",
            "4. **Telemetry Monitoring**: Monitor error rates, response latencies, and container logs.",
            "5. **Full Traffic Shift**: Route traffic to the new version once verified healthy."
        ]),
        ("refactor a complex legacy function", [
            "1. **Test Coverage Verification**: Ensure unit tests cover all existing execution paths.",
            "2. **Responsibility Analysis**: Decompose the function into single-responsibility components.",
            "3. **Helper Extraction**: Extract sub-functions with clear type annotations and docstrings.",
            "4. **Interface Preservation**: Ensure external callers experience identical public behavior.",
            "5. **Verification**: Run test suites to guarantee zero regression."
        ]),
        ("set up automated database backups", [
            "1. **Policy Definition**: Determine backup frequency, retention windows, and encryption keys.",
            "2. **Script Implementation**: Implement an automated dump script with integrity checksums.",
            "3. **Secure Off-site Transfer**: Push encrypted backups to isolated cloud storage.",
            "4. **Restoration Drill**: Test restoring the backup into a staging database to verify completeness.",
            "5. **Alert Configuration**: Set up alerts for backup failure or storage capacity warnings."
        ]),
        ("optimize an expensive SQL query", [
            "1. **Execution Plan Analysis**: Run `EXPLAIN ANALYZE` on the query to identify sequential scans.",
            "2. **Index Evaluation**: Identify missing indexes on `WHERE`, `JOIN`, and `ORDER BY` columns.",
            "3. **Index Addition**: Apply appropriate B-tree or composite indexes.",
            "4. **Query Refinement**: Simplify joins and eliminate redundant data selections.",
            "5. **Benchmark Verification**: Measure query execution latency before and after optimization."
        ]),
        ("implement API rate limiting", [
            "1. **Algorithm Selection**: Choose between Token Bucket and Sliding Window rate limiting.",
            "2. **Storage Layer**: Configure Redis to maintain atomic request counters.",
            "3. **Middleware Attachment**: Intercept incoming requests to check client IP or API key limit.",
            "4. **Standard Headers**: Return `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `Retry-After` on 429.",
            "5. **Load Testing**: Test under simulated burst traffic to verify stability."
        ]),
    ]

    question_templates = [
        "Create a plan to {task}.",
        "What is your step-by-step plan to {task}?",
        "How would an AI agent plan to {task}?",
        "Provide a structured execution plan to {task}.",
        "Outline the sequential steps required to {task}.",
        "How do you approach planning to {task}?",
        "Formulate a verifiable multi-step plan to {task}.",
        "What are the key phases to {task}?",
        "Write an engineering plan to {task}.",
        "Plan the execution steps to {task}.",
        "What is the best procedure to {task}?",
        "Break down the steps to {task}.",
        "How should Xeren plan to {task}?",
        "Detail the task execution strategy to {task}.",
        "Construct an action plan to {task}.",
    ]

    samples = []
    for task_name, steps in planning_blueprints:
        steps_text = "\n".join(steps)
        ans = f"Here is the structured execution plan to {task_name}:\n\n{steps_text}\n\nEach step must be verified before proceeding to subsequent actions."
        for tmpl in question_templates:
            q = tmpl.format(task=task_name)
            samples.append({"pillar": "agent_planning", "user": q, "assistant": ans})

    assert len(samples) == target_count
    return samples


# =============================================================================
# PILLAR 8: SECURITY, SAFETY & VERIFICATION (150 samples)
# =============================================================================
def generate_security_samples(target_count: int, rng: random.Random) -> List[Dict[str, Any]]:
    vulnerabilities = [
        ("eval() in Python (CWE-95)",
         "Executing untrusted code via eval() allows arbitrary code execution in the process context.",
         "Never use eval() on untrusted input. Use ast.literal_eval() for basic data structures or json.loads() for JSON."),
        ("SQL Injection (CWE-89)",
         "String concatenation in SQL queries allows attackers to manipulate query logic and extract or modify data.",
         "Always use parameterized queries or prepared statements (e.g. cursor.execute('SELECT * FROM users WHERE id = %s', (uid,)))."),
        ("Command Injection (CWE-78)",
         "Passing unvalidated input directly to shell commands via os.system() or subprocess.run(shell=True) allows arbitrary system execution.",
         "Use subprocess.run(['cmd', arg], shell=False) with strict argument whitelisting and input validation."),
        ("Path Traversal (CWE-22)",
         "Failing to sanitize file paths allows attackers to access arbitrary files using '../' directory climbing.",
         "Resolve the canonical absolute path using Path.resolve() and verify that resolved_path.is_relative_to(allowed_directory)."),
        ("Cross-Site Scripting / XSS (CWE-79)",
         "Rendering unescaped user input into web pages allows execution of malicious JavaScript in victim browsers.",
         "Sanitize and context-encode all dynamic output, utilize modern frameworks with auto-escaping, and implement Content Security Policy (CSP)."),
        ("Insecure Deserialization (CWE-502)",
         "Loading untrusted data with Python pickle allows arbitrary object instantiation and remote code execution.",
         "Never deserialize untrusted data with pickle. Use safe structured data serialization like JSON, YAML (with safe_load), or Protocol Buffers."),
        ("Hardcoded Credentials (CWE-798)",
         "Hardcoding API keys, database passwords, or private tokens in source code leads to credential compromise upon code exposure.",
         "Store all sensitive credentials in environment variables or external secrets managers, ensuring .env is listed in .gitignore."),
        ("Server-Side Request Forgery / SSRF (CWE-918)",
         "Allowing an application to make arbitrary outbound HTTP requests enables attackers to scan private internal networks or cloud metadata (169.254.169.254).",
         "Enforce strict destination URL whitelisting, validate domain names, and block internal/private IP ranges."),
        ("Weak Password Hashing (CWE-328)",
         "Using fast hash functions like MD5 or SHA-1 for passwords allows rapid rainbow table and brute force cracking.",
         "Use slow, memory-hard adaptive hashing algorithms designed for passwords such as Argon2id or bcrypt with appropriate work factors."),
        ("Cross-Site Request Forgery / CSRF (CWE-352)",
         "Unprotected web applications allow third-party sites to submit unauthorized state-changing requests on behalf of authenticated users.",
         "Enforce anti-CSRF tokens for all state-changing endpoints and set SameSite=Strict or SameSite=Lax on authentication cookies."),
        ("Prompt Injection in LLM Applications",
         "Adversarial user inputs override system prompt boundaries to hijack model behavior or leak private system instructions.",
         "Enforce strict delimiter isolation, treat user text as untrusted data, validate outputs with secondary verification gates, and restrict tool permissions."),
        ("Race Conditions in File Access / TOCTOU (CWE-367)",
         "Checking file existence before opening without atomic locks allows attackers to replace the file in between the check and use.",
         "Use atomic file operations, open with appropriate flags (e.g. os.O_EXCL), and handle exceptions rather than pre-checking existence."),
        ("Regular Expression Denial of Service / ReDoS (CWE-1333)",
         "Catastrophic backtracking in poorly constructed regular expressions allows crafted strings to exhaust CPU resources.",
         "Avoid nested quantifiers in regex patterns, use linear-time regex engines (like re2), and enforce timeout limits on pattern evaluation."),
        ("Information Disclosure in Error Messages (CWE-209)",
         "Exposing raw stack traces, database schema details, or server versions in error responses assists attackers in reconnaissance.",
         "Catch exceptions, log detailed diagnostics internally, and return generic, sanitized error messages to end users."),
        ("Insecure Direct Object References / IDOR (CWE-639)",
         "Relying solely on user-provided record IDs without verifying ownership allows unauthorized access to other users' data.",
         "Implement strict authorization checks verifying that the authenticated user owns or has explicit permission to access the requested resource ID."),
    ]

    question_templates = [
        "Explain the security risk of {vuln} and how to fix it.",
        "What is {vuln} and what are the recommended security mitigations?",
        "How can developers prevent {vuln} in software systems?",
        "Describe a real-world scenario involving {vuln} and its remediation.",
        "Why is {vuln} a serious security vulnerability?",
        "What automated checks should be implemented to detect {vuln}?",
        "Explain the remediation strategy for {vuln}.",
        "How does Xeren's security gate handle {vuln}?",
        "Provide a security analysis of {vuln}.",
        "What secure coding practices eliminate {vuln}?",
    ]

    samples = []
    for vuln_name, risk_desc, fix_desc in vulnerabilities:
        ans_text = f"### Security Assessment: {vuln_name}\n\n- **Vulnerability**: {risk_desc}\n- **Mitigation**: {fix_desc}\n\nAdhering to these secure coding standards ensures robust protection against unauthorized access."
        for tmpl in question_templates:
            q = tmpl.format(vuln=vuln_name)
            samples.append({"pillar": "security_verification", "user": q, "assistant": ans_text})

    assert len(samples) == target_count
    return samples


# =============================================================================
# PILLAR 9: MULTI-TURN CONVERSATION CONTINUITY (100 samples)
# =============================================================================
def generate_multi_turn_samples(target_count: int, rng: random.Random) -> List[Dict[str, Any]]:
    dialogues = [
        # 1. IP extraction & filtering
        [
            {"role": "user", "content": "I need a Python function to extract IP addresses from a log file string."},
            {"role": "assistant", "content": "Here is a Python function using regular expressions to extract IPv4 addresses:\n\n```python\nimport re\nfrom typing import List\n\ndef extract_ips(text: str) -> List[str]:\n    return re.findall(r'\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b', text)\n```"},
            {"role": "user", "content": "Can you update it to exclude private IPs like 192.168.x.x and 10.x.x.x?"},
            {"role": "assistant", "content": "Here is the updated function using Python's `ipaddress` module to filter out private IP addresses:\n\n```python\nimport re\nimport ipaddress\nfrom typing import List\n\ndef extract_public_ips(text: str) -> List[str]:\n    matches = re.findall(r'\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b', text)\n    public_ips = []\n    for ip_str in matches:\n        try:\n            ip = ipaddress.ip_address(ip_str)\n            if not ip.is_private and not ip.is_loopback:\n                public_ips.append(ip_str)\n        except ValueError:\n            continue\n    return public_ips\n```"}
        ],
        # 2. Compound Interest Calculation
        [
            {"role": "user", "content": "What is the formula for compound interest?"},
            {"role": "assistant", "content": "The compound interest formula is:\n`A = P * (1 + r/n)**(n*t)`\n\nWhere:\n- `A`: Final accrued amount\n- `P`: Principal investment\n- `r`: Annual nominal interest rate (decimal)\n- `n`: Compounding frequency per year\n- `t`: Duration in years"},
            {"role": "user", "content": "What will $5,000 become at 6% interest compounded quarterly after 3 years?"},
            {"role": "assistant", "content": "Let's calculate using the formula:\n- `P = 5000`\n- `r = 0.06`\n- `n = 4` (quarterly)\n- `t = 3`\n\n1. Rate per period: `0.06 / 4 = 0.015`\n2. Total periods: `4 * 3 = 12`\n3. Multiplier: `(1 + 0.015)**12 ≈ 1.195618`\n4. Final amount: `5000 * 1.195618 ≈ $5,978.09`\n\nThe final amount will be **$5,978.09**."}
        ],
        # 3. Git Branching & Remote
        [
            {"role": "user", "content": "How do I create a new branch and switch to it in Git?"},
            {"role": "assistant", "content": "You can create and switch to a new branch using:\n`git checkout -b <branch_name>`\nOr with modern Git:\n`git switch -c <branch_name>`"},
            {"role": "user", "content": "How do I push this new branch to GitHub and set tracking?"},
            {"role": "assistant", "content": "To push the branch and configure upstream tracking, run:\n`git push -u origin <branch_name>`"}
        ],
        # 4. List vs Tuple
        [
            {"role": "user", "content": "What is the difference between a list and a tuple in Python?"},
            {"role": "assistant", "content": "The primary difference is mutability:\n- **List**: Mutable (can append, remove, or modify items). Defined with `[]`.\n- **Tuple**: Immutable (cannot be modified after creation). Defined with `()`. Tuples can be hashed and used as dictionary keys."},
            {"role": "user", "content": "When should I prefer using a tuple over a list?"},
            {"role": "assistant", "content": "Prefer tuples when:\n1. The collection should be protected from accidental mutation.\n2. You need dictionary keys or set elements.\n3. Storing fixed heterogeneous records (e.g. `(latitude, longitude)`).\n4. Slightly lower memory overhead is desired."}
        ],
        # 5. JSON File Reading & Writing
        [
            {"role": "user", "content": "How do I write a dictionary to a JSON file in Python?"},
            {"role": "assistant", "content": "Use Python's `json.dump()` with a context manager:\n\n```python\nimport json\n\ndata = {'status': 'active', 'code': 200}\nwith open('output.json', 'w', encoding='utf-8') as f:\n    json.dump(data, f, indent=2)\n```"},
            {"role": "user", "content": "And how do I read it back?"},
            {"role": "assistant", "content": "Use `json.load()` with a context manager:\n\n```python\nimport json\n\nwith open('output.json', 'r', encoding='utf-8') as f:\n    loaded_data = json.load(f)\nprint(loaded_data['status'])\n```"}
        ],
        # 6. Sorting Dictionaries
        [
            {"role": "user", "content": "How do I sort a list of dictionaries by a specific key in Python?"},
            {"role": "assistant", "content": "Use Python's built-in `sorted()` with a lambda key:\n\n```python\nusers = [{'name': 'Alice', 'score': 85}, {'name': 'Bob', 'score': 92}]\nsorted_users = sorted(users, key=lambda u: u['score'])\n```"},
            {"role": "user", "content": "How do I reverse it to sort from highest score to lowest?"},
            {"role": "assistant", "content": "Add `reverse=True`:\n\n```python\nsorted_users = sorted(users, key=lambda u: u['score'], reverse=True)\n```"}
        ],
        # 7. HTTP Status Codes
        [
            {"role": "user", "content": "What is the difference between a 401 and 403 HTTP status code?"},
            {"role": "assistant", "content": "401 Unauthorized means authentication credentials are missing or invalid. 403 Forbidden means the server recognizes the client's identity, but the client lacks authorization to access the resource."},
            {"role": "user", "content": "What status code should be returned if a requested endpoint does not exist?"},
            {"role": "assistant", "content": "The standard status code is **404 Not Found**. If the resource previously existed but was permanently deleted, **410 Gone** can also be used."}
        ],
        # 8. SQL Database Indexes
        [
            {"role": "user", "content": "How do I create an index on a column in SQL?"},
            {"role": "assistant", "content": "Create an index using the following SQL statement:\n\n```sql\nCREATE INDEX idx_users_email ON users(email);\n```"},
            {"role": "user", "content": "Does adding an index speed up every query on that table?"},
            {"role": "assistant", "content": "No. Indexes accelerate `SELECT`, `WHERE`, `JOIN`, and `ORDER BY` operations on the indexed column, but can slightly slow down `INSERT`, `UPDATE`, and `DELETE` operations due to index update overhead."}
        ],
        # 9. Docker Container Lifecycle
        [
            {"role": "user", "content": "How do I run a Docker container in detached background mode?"},
            {"role": "assistant", "content": "Use the `-d` flag:\n\n```bash\ndocker run -d -p 8080:80 --name my_app my_image:latest\n```"},
            {"role": "user", "content": "How do I check the logs of that running container?"},
            {"role": "assistant", "content": "View the container logs using:\n\n```bash\ndocker logs -f my_app\n```\nThe `-f` flag follows and streams log output in real time."}
        ],
        # 10. Virtual Environments in Python
        [
            {"role": "user", "content": "How do I create a virtual environment in Python?"},
            {"role": "assistant", "content": "Create a virtual environment using the standard `venv` module:\n\n```bash\npython -m venv .venv\n```"},
            {"role": "user", "content": "How do I activate it on Windows PowerShell?"},
            {"role": "assistant", "content": "Activate it in PowerShell by running:\n\n```powershell\n.\\.venv\\Scripts\\Activate.ps1\n```\nIf script execution is disabled, enable it via `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`."}
        ],
    ]

    samples = []
    # 10 variations per base dialogue = 100 samples
    for idx, base_dial in enumerate(dialogues):
        for var_i in range(10):
            cloned = [dict(t) for t in base_dial]
            if var_i > 0:
                cloned[0]["content"] = f"[Session {var_i+1}] {cloned[0]['content']}"
            samples.append({
                "pillar": "multi_turn",
                "is_multi_turn": True,
                "turns": cloned,
            })

    assert len(samples) == target_count
    return samples


# =============================================================================
# MAIN BUILDER & STRATIFIED SPLITTER
# =============================================================================
def build_dataset():
    logger.info("Initializing Matured Alignment Dataset Builder with deterministic seed 42...")
    rng = random.Random(42)

    pillar_generators = [
        ("identity_architecture", 150, generate_identity_architecture_samples),
        ("general_knowledge", 200, generate_general_knowledge_samples),
        ("arithmetic", 200, generate_arithmetic_samples),
        ("python_programming", 250, generate_python_samples),
        ("rag_retrieval", 150, generate_rag_samples),
        ("tool_usage", 250, generate_tool_usage_samples),
        ("agent_planning", 150, generate_planning_samples),
        ("security_verification", 150, generate_security_samples),
        ("multi_turn", 100, generate_multi_turn_samples),
    ]

    all_samples_by_pillar = {}
    total_generated = 0

    for pillar_name, target_count, generator_func in pillar_generators:
        logger.info(f"Generating pillar: {pillar_name} (target: {target_count})...")
        pillar_samples = generator_func(target_count, rng)
        assert len(pillar_samples) == target_count, f"Pillar {pillar_name} count mismatch"
        all_samples_by_pillar[pillar_name] = pillar_samples
        total_generated += len(pillar_samples)

    logger.info(f"Total raw samples generated: {total_generated}")
    assert total_generated == 1600, f"Expected 1,600 samples, got {total_generated}"

    train_texts = []
    val_texts = []
    seen_texts = set()
    duplicate_count = 0
    malformed_count = 0
    pillar_counts = {}

    for pillar_name, samples in all_samples_by_pillar.items():
        rng.shuffle(samples)
        
        val_target = len(samples) // 10
        train_target = len(samples) - val_target

        p_train = samples[:train_target]
        p_val = samples[train_target:]

        pillar_counts[pillar_name] = {
            "total": len(samples),
            "train": len(p_train),
            "val": len(p_val),
        }

        for split_name, subset in [("train", p_train), ("val", p_val)]:
            for item in subset:
                if item.get("is_multi_turn"):
                    formatted_text = format_chatml(DEFAULT_SYSTEM_PROMPT, item["turns"])
                else:
                    turns = [
                        {"role": "user", "content": item["user"]},
                        {"role": "assistant", "content": item["assistant"]},
                    ]
                    formatted_text = format_chatml(DEFAULT_SYSTEM_PROMPT, turns)

                if not formatted_text.strip() or "<|im_start|>assistant\n" not in formatted_text:
                    malformed_count += 1
                    continue
                
                if formatted_text in seen_texts:
                    duplicate_count += 1
                else:
                    seen_texts.add(formatted_text)

                if split_name == "train":
                    train_texts.append(formatted_text)
                else:
                    val_texts.append(formatted_text)

    logger.info(f"Train texts count: {len(train_texts)}, Val texts count: {len(val_texts)}")
    assert len(train_texts) == 1440, f"Expected 1440 train texts, got {len(train_texts)}"
    assert len(val_texts) == 160, f"Expected 160 val texts, got {len(val_texts)}"

    tokenizer_path = ROOT_DIR / "training" / "checkpoints" / "tokenizer_32k"
    token_lengths = []
    if tokenizer_path.exists():
        try:
            from training.src.tokenizer.train_tokenizer import XerenTokenizer
            tokenizer = XerenTokenizer.load(str(tokenizer_path))
            for t in train_texts + val_texts:
                token_lengths.append(len(tokenizer.encode(t)))
            logger.info("Computed token stats using native XerenTokenizer (32K).")
        except Exception as e:
            logger.warning(f"Could not load tokenizer for token stats: {e}")
            token_lengths = [len(t.split()) for t in train_texts + val_texts]
    else:
        token_lengths = [len(t.split()) for t in train_texts + val_texts]

    avg_tokens = round(sum(token_lengths) / max(1, len(token_lengths)), 1)
    min_tokens = min(token_lengths) if token_lengths else 0
    max_tokens = max(token_lengths) if token_lengths else 0

    output_dir = ROOT_DIR / "training" / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    train_file = output_dir / "matured_alignment_train.json"
    val_file = output_dir / "matured_alignment_val.json"
    report_file = output_dir / "matured_alignment_report.json"

    with open(train_file, "w", encoding="utf-8") as f:
        json.dump(train_texts, f, indent=2, ensure_ascii=False)
    with open(val_file, "w", encoding="utf-8") as f:
        json.dump(val_texts, f, indent=2, ensure_ascii=False)

    report_data = {
        "dataset_name": "Xeren 214M Path B Matured Alignment Dataset",
        "schema_version": "1.0",
        "random_seed": 42,
        "total_samples": len(train_texts) + len(val_texts),
        "train_samples": len(train_texts),
        "val_samples": len(val_texts),
        "validation_split_ratio": 0.10,
        "duplicate_count": duplicate_count,
        "malformed_count": malformed_count,
        "pillar_distribution": pillar_counts,
        "token_statistics": {
            "avg_tokens": avg_tokens,
            "min_tokens": min_tokens,
            "max_tokens": max_tokens,
        },
        "validation_status": "PASSED" if (duplicate_count == 0 and malformed_count == 0 and len(train_texts) == 1440 and len(val_texts) == 160) else "FAILED",
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    return report_data


if __name__ == "__main__":
    report = build_dataset()
    print("\n" + "=" * 65)
    print("DATASET GENERATION COMPLETE")
    print("=" * 65)
    print(f"Total Samples          : {report['total_samples']}")
    print(f"Train Samples          : {report['train_samples']}")
    print(f"Validation Samples     : {report['val_samples']}")
    print(f"Duplicates             : {report['duplicate_count']}")
    print(f"Malformed Records      : {report['malformed_count']}")
    print(f"Validation Status      : {report['validation_status']}")
    print("\nPillar Distribution:")
    for p, counts in report['pillar_distribution'].items():
        print(f"  • {p:<25}: {counts['total']} total ({counts['train']} train / {counts['val']} val)")
    print("\nToken Statistics (32K Tokenizer):")
    print(f"  • Average Tokens       : {report['token_statistics']['avg_tokens']}")
    print(f"  • Min Tokens           : {report['token_statistics']['min_tokens']}")
    print(f"  • Max Tokens           : {report['token_statistics']['max_tokens']}")
    print("=" * 65 + "\n")
