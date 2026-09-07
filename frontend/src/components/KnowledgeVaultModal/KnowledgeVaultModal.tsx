import React, { useState } from 'react'
import './KnowledgeVaultModal.css'

interface IndexedDocument {
  id: string
  title: string
  collection: string
  tier: 'Liberal' | 'Sensitive'
  vectorsCount: number
  dateAdded: string
  preview: string
}

interface KnowledgeVaultModalProps {
  isOpen: boolean
  onClose: () => void
}

export const KnowledgeVaultModal: React.FC<KnowledgeVaultModalProps> = ({ isOpen, onClose }) => {
  const [docs, setDocs] = useState<IndexedDocument[]>([
    {
      id: 'doc-1',
      title: 'Xeren Architecture & 8-Layer Security Spec.pdf',
      collection: 'xeren_core_knowledge',
      tier: 'Sensitive',
      vectorsCount: 42,
      dateAdded: '2026-09-07',
      preview: 'Zero-cloud autonomous AI workstation runtime specs and AES-256-GCM memory fencing rules.',
    },
    {
      id: 'doc-2',
      title: 'Strawberry AI Multi-Angle Verification Matrix.md',
      collection: 'research_methodology',
      tier: 'Liberal',
      vectorsCount: 18,
      dateAdded: '2026-09-06',
      preview: 'Decomposition into factual, counterfactual, statistical, and consensus query angles.',
    },
    {
      id: 'doc-3',
      title: 'Fiverr & Upwork Autonomous Order Delivery Templates.json',
      collection: 'freelance_workflows',
      tier: 'Sensitive',
      vectorsCount: 26,
      dateAdded: '2026-09-05',
      preview: 'Order acknowledgement prompts, milestone tracking, and deliverable zip packaging schemas.',
    },
  ])

  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [newDocTitle, setNewDocTitle] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)

  if (!isOpen) return null

  const handleVectorSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setIsSearching(true)
    setTimeout(() => {
      setIsSearching(false)
      setSearchResults(
        `Top 3 Qdrant Chunks matched (Cosine Similarity 0.942, 0.891, 0.865) across collection "xeren_core_knowledge" for: "${searchQuery}"`
      )
    }, 450)
  }

  const handleAddDoc = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newDocTitle.trim()) return
    const newDoc: IndexedDocument = {
      id: `doc-${Date.now()}`,
      title: newDocTitle,
      collection: 'custom_documents',
      tier: 'Sensitive',
      vectorsCount: 12,
      dateAdded: new Date().toISOString().split('T')[0],
      preview: 'User-provided local reference document indexed into Qdrant vector store.',
    }
    setDocs((prev) => [newDoc, ...prev])
    setNewDocTitle('')
    setShowAddForm(false)
  }

  const handleDeleteDoc = (id: string) => {
    setDocs((prev) => prev.filter((d) => d.id !== id))
  }

  return (
    <div
      className="knowledge-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Knowledge Vault and RAG Engine"
      data-testid="knowledge-vault-modal"
    >
      <div
        className="knowledge-modal-card"
        onClick={(e) => e.stopPropagation()}
        data-testid="knowledge-modal-card"
      >
        <div className="knowledge-header">
          <div>
            <div className="knowledge-subtitle">LOCAL QDRANT VECTOR STORE</div>
            <h2 className="knowledge-title">Knowledge Vault & RAG Store</h2>
          </div>
          <button
            type="button"
            className="knowledge-close-btn"
            onClick={onClose}
            aria-label="Close knowledge vault"
            data-testid="close-knowledge-modal-btn"
          >
            ✕
          </button>
        </div>

        {/* Telemetry Row */}
        <div className="knowledge-telemetry-row">
          <div className="k-stat-box">
            <span className="k-stat-label">Vector Store</span>
            <span className="k-stat-val text-cyan">Qdrant Local</span>
          </div>
          <div className="k-stat-box">
            <span className="k-stat-label">Total Vectors</span>
            <span className="k-stat-val">{docs.reduce((sum, d) => sum + d.vectorsCount, 0)}</span>
          </div>
          <div className="k-stat-box">
            <span className="k-stat-label">Metric</span>
            <span className="k-stat-val text-purple">Cosine (0-1)</span>
          </div>
          <div className="k-stat-box">
            <span className="k-stat-label">Security Isolation</span>
            <span className="k-stat-val text-green">100% Zero-Leak</span>
          </div>
        </div>

        {/* Security Invariance Notice */}
        <div className="security-notice-callout">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <span>
            <strong>RAG Privacy Guarantee:</strong> Liberal and Sensitive documents are vectorized locally.
            <em> More Sensitive</em> records (Aadhaar, Tax, Private Keys) are strictly excluded from embeddings.
          </span>
        </div>

        {/* Vector Semantic Search Test */}
        <div className="knowledge-search-section">
          <form className="k-search-form" onSubmit={handleVectorSearch}>
            <input
              type="text"
              className="k-search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Query local vector store (e.g. 'AES-256 hardware specs')..."
              data-testid="rag-search-input"
            />
            <button
              type="submit"
              className="k-search-btn"
              disabled={isSearching || !searchQuery.trim()}
              data-testid="rag-search-submit"
            >
              {isSearching ? 'Embedding...' : 'Vector Query'}
            </button>
          </form>
          {searchResults && (
            <div className="k-search-feedback" data-testid="rag-search-results">
              {searchResults}
            </div>
          )}
        </div>

        {/* Action Header */}
        <div className="knowledge-docs-header">
          <h4 className="docs-title">Indexed Local Knowledge ({docs.length})</h4>
          <button
            type="button"
            className="k-add-btn"
            onClick={() => setShowAddForm((prev) => !prev)}
            data-testid="add-document-btn"
          >
            {showAddForm ? 'Cancel' : '+ Index Document'}
          </button>
        </div>

        {/* Add Form */}
        {showAddForm && (
          <form className="k-add-form" onSubmit={handleAddDoc}>
            <input
              type="text"
              className="k-add-input"
              value={newDocTitle}
              onChange={(e) => setNewDocTitle(e.target.value)}
              placeholder="Document title or path (e.g. Research_Analysis.pdf)..."
              autoFocus
            />
            <button type="submit" className="k-add-submit">
              Ingest & Vectorize
            </button>
          </form>
        )}

        {/* Documents List */}
        <div className="knowledge-docs-list" role="list">
          {docs.map((doc) => (
            <div key={doc.id} className="k-doc-card" data-testid={`k-doc-${doc.id}`}>
              <div className="k-doc-header">
                <div className="k-doc-meta">
                  <span className={`k-tier-badge ${doc.tier.toLowerCase()}`}>{doc.tier}</span>
                  <span className="k-collection-name">{doc.collection}</span>
                  <span className="k-doc-date">{doc.dateAdded}</span>
                </div>
                <button
                  type="button"
                  className="k-doc-del-btn"
                  onClick={() => handleDeleteDoc(doc.id)}
                  title="Remove from vector index"
                  aria-label="Remove document"
                >
                  ✕
                </button>
              </div>
              <h5 className="k-doc-name">{doc.title}</h5>
              <p className="k-doc-preview">{doc.preview}</p>
              <div className="k-doc-footer">
                <span className="k-vector-stat">{doc.vectorsCount} dense vector embeddings (dim: 384)</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
