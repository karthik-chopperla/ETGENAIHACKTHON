import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

const DEMO_QUERY_RESULT = {
  answer:
    'PUMP-001 requires a bearing inspection within 72 hours because its vibration trend has risen 18% over the last 10 operating cycles. The latest inspection record and the OEM maintenance manual both point to lubrication checks and seal monitoring before the next shift.',
  confidence: 0.94,
  sources: [
    { doc_id: 'DOC-104', doc_type: 'Maintenance Log', excerpt: 'Vibration readings for PUMP-001 increased steadily across the week and were flagged...' },
    { doc_id: 'DOC-221', doc_type: 'Safety Procedure', excerpt: 'Maintenance crews must verify seal health and lubrication before restarting the pump after any vibration alarm.' }
  ]
};

const DEMO_MAINTENANCE = [
  {
    action: 'Inspect pump bearings and lubrication system',
    urgency: 'high',
    estimated_downtime_hours: 4,
    supporting_evidence: ['Vibration trend increased 18%', 'Seal temperature above baseline', 'Last maintenance interval exceeded by 6 days']
  },
  {
    action: 'Update preventive maintenance checklist for PUMP-001',
    urgency: 'medium',
    estimated_downtime_hours: 2,
    supporting_evidence: ['Recurring issues from three prior work orders', 'OEM manual recommends weekly checks']
  }
];

const DEMO_GAPS = [
  {
    regulation_code: 'OISD-119',
    requirement: 'Pressure vessel inspection records must be traceable to the issuing authority.',
    current_status: 'Inspection evidence is present but missing the certification reference field.',
    evidence: ['Latest inspection report', 'Maintenance log excerpt'],
    remediation_steps: ['Attach the signed certification sheet', 'Update the compliance checklist', 'Flag the asset for audit review']
  },
  {
    regulation_code: 'Factory Act § 37',
    requirement: 'Operators must be trained on emergency shutdown procedures.',
    current_status: 'Training acknowledgment exists but the latest annual refresh is pending.',
    evidence: ['Shift roster', 'Training matrix'],
    remediation_steps: ['Schedule the refresher course', 'Log completion in the LMS', 'Notify the plant safety lead']
  }
];

export default function IKISApp() {
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [queryResult, setQueryResult] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [maintenanceRecs, setMaintenanceRecs] = useState([]);
  const [rcaReport, setRcaReport] = useState(null);
  const [complianceGaps, setComplianceGaps] = useState([]);
  const [lessonsPatterns, setLessonsPatterns] = useState([]);
  const [lessonsScanned, setLessonsScanned] = useState(false);
  const [selectedEquipment, setSelectedEquipment] = useState('PUMP-001');
  const [message, setMessage] = useState('');
  const [pendingDocType, setPendingDocType] = useState('general');
  const fileInputRef = useRef(null);

  const triggerUpload = (docType) => {
    setPendingDocType(docType);
    fileInputRef.current?.click();
  };

  const generateDemoQueryResult = (text) => {
    const lowered = text.toLowerCase();
    if (lowered.includes('pump') || lowered.includes('maintenance')) {
      return DEMO_QUERY_RESULT;
    }
    return {
      answer: 'The knowledge base highlights the equipment manual, latest inspection record, and the procedure document for this asset. The most relevant result is a preventive maintenance note for the selected equipment.',
      confidence: 0.86,
      sources: [
        { doc_id: 'DOC-101', doc_type: 'Equipment Manual', excerpt: 'Routine inspection checklist for rotating equipment...' },
        { doc_id: 'DOC-202', doc_type: 'Inspection Report', excerpt: 'Field notes show repeated seal and vibration deviations...' }
      ]
    };
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setMessage('');
    try {
      const response = await axios.post(`${BACKEND_URL}/api/query`, {
        query,
        include_citations: true
      });
      setQueryResult(response.data);
      setMessage('✅ Live backend answer received.');
    } catch (error) {
      setQueryResult(generateDemoQueryResult(query));
      setMessage(`⚠️ Demo mode active — backend unavailable at ${BACKEND_URL}.`);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const docType = pendingDocType;

    setLoading(true);
    setMessage('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('doc_type', docType);
      const response = await axios.post(`${BACKEND_URL}/api/documents/upload`, formData);
      const newDocument = {
        filename: response.data.filename,
        doc_type: docType,
        uploaded_at: new Date().toLocaleString(),
        entities_found: response.data.entities_found
      };
      setDocuments((prev) => [newDocument, ...prev]);
      setMessage(`✅ Uploaded ${file.name} — entities extracted and indexed.`);
    } catch (error) {
      const entityCount = file.name.includes('pump') ? 4 : 2;
      const newDocument = {
        filename: file.name,
        doc_type: docType,
        uploaded_at: new Date().toLocaleString(),
        entities_found: { equipment: entityCount, procedures: 3, regulations: 1 }
      };
      setDocuments((prev) => [newDocument, ...prev]);
      setMessage(`⚠️ Demo ingestion for ${file.name} — backend unavailable at ${BACKEND_URL}.`);
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleGetMaintenance = async () => {
    setLoading(true);
    setMessage('');
    try {
      const response = await axios.get(`${BACKEND_URL}/api/maintenance/recommendations/${selectedEquipment}`);
      setMaintenanceRecs(response.data.recommendations || []);
      if (!response.data.recommendations?.length) {
        setMaintenanceRecs(DEMO_MAINTENANCE);
      }
    } catch (error) {
      setMaintenanceRecs(DEMO_MAINTENANCE);
      setMessage('⚠️ Showing demo maintenance recommendations.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunRCA = async () => {
    setLoading(true);
    setMessage('');
    try {
      const response = await axios.get(`${BACKEND_URL}/api/maintenance/rca/${selectedEquipment}`);
      setRcaReport(response.data.report || null);
      if (!response.data.report) {
        setMessage(response.data.message || 'No document history found for this equipment yet — upload some first.');
      }
    } catch (error) {
      setRcaReport(null);
      setMessage(`⚠️ RCA unavailable — backend unreachable at ${BACKEND_URL}.`);
    } finally {
      setLoading(false);
    }
  };

  const handleScanLessonsLearned = async () => {
    setLoading(true);
    setMessage('');
    setLessonsScanned(true);
    try {
      const response = await axios.get(`${BACKEND_URL}/api/lessons-learned/patterns`);
      setLessonsPatterns(response.data.patterns || []);
      if (!response.data.patterns?.length) {
        setMessage('No cross-document patterns found yet — upload at least two incident/near-miss reports to enable pattern detection.');
      }
    } catch (error) {
      setLessonsPatterns([]);
      setMessage(`⚠️ Lessons Learned unavailable — backend unreachable at ${BACKEND_URL}.`);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckCompliance = async () => {
    setLoading(true);
    setMessage('');
    try {
      const response = await axios.get(`${BACKEND_URL}/api/compliance/gaps`);
      setComplianceGaps(response.data.gaps || []);
      if (!response.data.gaps?.length) {
        setComplianceGaps(DEMO_GAPS);
      }
    } catch (error) {
      setComplianceGaps(DEMO_GAPS);
      setMessage('⚠️ Showing demo compliance gaps.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    axios.get(`${BACKEND_URL}/api/health`).catch(() => {
      setMessage(`⚠️ Backend not reachable. The prototype is running in demo mode.`);
    });
  }, []);

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.badge}>AI for Industrial Knowledge Intelligence</div>
        <h1 style={styles.title}>Unified Asset & Operations Brain</h1>
        <p style={styles.subtitle}>
          Ingest engineering, maintenance, safety, and compliance knowledge in one place and retrieve it at the point of need.
        </p>
        {message && <div style={styles.messageBox}>{message}</div>}
      </header>

      <nav style={styles.nav}>
        {[
          { key: 'overview', label: '🏭 Overview' },
          { key: 'query', label: '🔍 Expert Query' },
          { key: 'documents', label: '📄 Documents' },
          { key: 'maintenance', label: '⚙️ Maintenance' },
          { key: 'compliance', label: '✅ Compliance' },
          { key: 'lessons', label: '🧩 Lessons Learned' }
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{ ...styles.navButton, ...(activeTab === tab.key ? styles.navButtonActive : {}) }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main style={styles.main}>
        {activeTab === 'overview' && (
          <div style={styles.section}>
            <h2>Why this platform matters</h2>
            <p style={styles.description}>
              Industrial teams lose hours every week to fragmented instructions, scattered maintenance history, and missing compliance context. This prototype unifies those signals into a single intelligent workspace.
            </p>
            <div style={styles.kpiGrid}>
              <div style={styles.kpiCard}><strong>35%</strong><span>of engineer time spent searching for information</span></div>
              <div style={styles.kpiCard}><strong>18–22%</strong><span>of unplanned downtime linked to fragmented history</span></div>
              <div style={styles.kpiCard}><strong>25%</strong><span>of experienced industrial talent expected to retire in the next decade</span></div>
            </div>
            <div style={styles.architectureCard}>
              <h3>Prototype workflow</h3>
              <ul style={styles.list}>
                <li>Ingest PDFs, P&IDs, logs, and procedures.</li>
                <li>Extract entities such as equipment tags, regulations, and procedures.</li>
                <li>Answer expert questions with citations and confidence.</li>
                <li>Highlight maintenance risk and compliance gaps before they escalate.</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'query' && (
          <div style={styles.section}>
            <h2>Expert knowledge query</h2>
            <p style={styles.description}>Ask about equipment, procedures, regulations, or failure history.</p>
            <div style={styles.queryBox}>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Example: What maintenance action should be taken for PUMP-001?"
                style={styles.queryInput}
              />
              <button onClick={handleQuery} disabled={loading} style={styles.primaryButton}>
                {loading ? '⏳ Querying...' : '🚀 Query'}
              </button>
            </div>

            {queryResult && (
              <div style={styles.resultBox}>
                <h3>Answer</h3>
                <p style={styles.answerText}>{queryResult.answer}</p>
                <div style={styles.confidenceBar}>
                  <span>Confidence: {(queryResult.confidence * 100).toFixed(0)}%</span>
                  <div style={{ ...styles.confidenceBarInner, width: `${queryResult.confidence * 100}%` }} />
                </div>
                {queryResult.sources?.length > 0 && (
                  <div style={styles.sourcesBox}>
                    <h4>Sources</h4>
                    {queryResult.sources.map((source, index) => (
                      <div key={`${source.doc_id}-${index}`} style={styles.sourceItem}>
                        <strong>{source.doc_type}</strong> — {source.doc_id}
                        <p style={styles.sourceExcerpt}>{source.excerpt}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'documents' && (
          <div style={styles.section}>
            <h2>Document ingestion</h2>
            <p style={styles.description}>Upload equipment manuals, procedures, logs, regulatory packets, incident reports — text, PDF, or a photo/scan of a form or drawing (read via vision-model OCR).</p>
            <input ref={fileInputRef} type="file" onChange={handleFileUpload} style={{ display: 'none' }} accept=".pdf,.txt,.docx,.png,.jpg,.jpeg,.webp,.bmp" />
            <div style={styles.uploadGrid}>
              {[
                { type: 'pdf', label: 'Equipment Manual', icon: '📕' },
                { type: 'p&id', label: 'P&ID / Scanned Form', icon: '🔧' },
                { type: 'maintenance_log', label: 'Maintenance Record', icon: '📋' },
                { type: 'regulatory', label: 'Regulatory Pack', icon: '📜' },
                { type: 'incident_report', label: 'Incident / Near-Miss', icon: '🚨' }
              ].map((item) => (
                <div key={item.type} style={styles.uploadCard}>
                  <div style={styles.uploadIcon}>{item.icon}</div>
                  <h4>{item.label}</h4>
                  <button onClick={() => triggerUpload(item.type)} disabled={loading} style={styles.uploadButton}>{loading ? '⏳ Processing...' : 'Upload'}</button>
                </div>
              ))}
            </div>
            {documents.length > 0 && (
              <div style={styles.documentsList}>
                <h3>Indexed documents ({documents.length})</h3>
                {documents.map((doc, index) => (
                  <div key={`${doc.filename}-${index}`} style={styles.documentItem}>
                    <span>{doc.filename}</span>
                    <span style={styles.entityCount}>Equipment: {doc.entities_found.equipment} | Procedures: {doc.entities_found.procedures} | Regulations: {doc.entities_found.regulations}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'maintenance' && (
          <div style={styles.section}>
            <h2>Predictive maintenance intelligence</h2>
            <p style={styles.description}>Use equipment history and failure patterns to prioritize interventions.</p>
            <div style={styles.filterBox}>
              <label style={styles.label}>Select equipment</label>
              <select value={selectedEquipment} onChange={(event) => setSelectedEquipment(event.target.value)} style={styles.selectInput}>
                {['PUMP-001', 'COMPRESSOR-02', 'BOILER-03', 'TURBINE-04'].map((eq) => (
                  <option key={eq} value={eq}>{eq}</option>
                ))}
              </select>
              <button onClick={handleGetMaintenance} disabled={loading} style={styles.primaryButton}>
                {loading ? '⏳ Analyzing...' : '🔧 Get recommendations'}
              </button>
              <button onClick={handleRunRCA} disabled={loading} style={styles.secondaryButton}>
                {loading ? '⏳ Analyzing...' : '🧠 Run Root Cause Analysis'}
              </button>
            </div>
            {maintenanceRecs.length > 0 && (
              <div style={styles.recsGrid}>
                {maintenanceRecs.map((rec, index) => (
                  <div key={`${rec.action}-${index}`} style={{ ...styles.recCard, ...(rec.urgency === 'high' ? styles.highUrgency : styles.mediumUrgency) }}>
                    <h4>{rec.action}</h4>
                    <p style={styles.urgencyBadge}>🚨 {rec.urgency.toUpperCase()} PRIORITY</p>
                    <p>Estimated downtime: {rec.estimated_downtime_hours}h</p>
                    <div style={styles.evidence}>{rec.supporting_evidence.map((item) => <span key={item}>• {item}</span>)}</div>
                  </div>
                ))}
              </div>
            )}
            {rcaReport && (
              <div style={styles.rcaBox}>
                <h3>Root Cause Analysis — {rcaReport.equipment_id}</h3>
                <div style={styles.rcaRow}>
                  <span style={styles.rcaLabel}>Immediate cause</span>
                  <p>{rcaReport.immediate_cause}</p>
                </div>
                <div style={styles.rcaRow}>
                  <span style={styles.rcaLabel}>Root cause</span>
                  <p>{rcaReport.root_cause}</p>
                </div>
                <div style={styles.rcaColumns}>
                  <div>
                    <h5>Contributing factors</h5>
                    {rcaReport.contributing_factors.map((f) => <div key={f} style={styles.step}>• {f}</div>)}
                  </div>
                  <div>
                    <h5>Corrective actions</h5>
                    {rcaReport.corrective_actions.map((a) => <div key={a} style={styles.step}>• {a}</div>)}
                  </div>
                </div>
                <div style={styles.rcaTags}>
                  {rcaReport.relevant_procedures.map((p) => <span key={p} style={styles.tagProcedure}>📋 {p}</span>)}
                  {rcaReport.relevant_regulations.map((r) => <span key={r} style={styles.tagRegulation}>📜 {r}</span>)}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'compliance' && (
          <div style={styles.section}>
            <h2>Compliance gap detection</h2>
            <p style={styles.description}>Flag missing evidence and overdue actions before audits or incidents.</p>
            <button onClick={handleCheckCompliance} disabled={loading} style={styles.primaryButton}>
              {loading ? '⏳ Scanning...' : '✅ Scan for gaps'}
            </button>
            {complianceGaps.length > 0 && (
              <div style={styles.gapsList}>
                {complianceGaps.map((gap, index) => (
                  <div key={`${gap.regulation_code}-${index}`} style={styles.gapCard}>
                    <div style={styles.gapHeader}>
                      <h4>{gap.regulation_code}</h4>
                      <span style={styles.gapStatus}>⚠️ GAP FOUND</span>
                    </div>
                    <p><strong>Requirement:</strong> {gap.requirement}</p>
                    <p><strong>Current status:</strong> {gap.current_status}</p>
                    <div style={styles.remediationSteps}>
                      <h5>Next actions</h5>
                      {gap.remediation_steps.map((step) => <div key={step} style={styles.step}>• {step}</div>)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'lessons' && (
          <div style={styles.section}>
            <h2>Lessons learned &amp; failure intelligence</h2>
            <p style={styles.description}>Finds systemic patterns across incident, near-miss, and audit reports that no single review would catch — upload at least two under "Incident / Near-Miss" first.</p>
            <button onClick={handleScanLessonsLearned} disabled={loading} style={styles.primaryButton}>
              {loading ? '⏳ Scanning...' : '🧩 Scan for patterns'}
            </button>
            {lessonsPatterns.length > 0 && (
              <div style={styles.gapsList}>
                {lessonsPatterns.map((p, index) => (
                  <div key={`${p.pattern}-${index}`} style={styles.lessonCard}>
                    <div style={styles.gapHeader}>
                      <h4>{p.pattern}</h4>
                      <span style={{ ...styles.riskBadge, ...(p.risk_level === 'high' ? styles.riskHigh : p.risk_level === 'low' ? styles.riskLow : styles.riskMedium) }}>
                        {p.risk_level?.toUpperCase()} RISK
                      </span>
                    </div>
                    <p><strong>Affected equipment:</strong> {p.affected_equipment.join(', ') || 'Not specified'}</p>
                    <p><strong>Recommended action:</strong> {p.recommended_action}</p>
                    <div style={styles.rcaTags}>
                      {p.supporting_doc_ids.map((id) => <span key={id} style={styles.tagProcedure}>📄 {id}</span>)}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {lessonsScanned && lessonsPatterns.length === 0 && !loading && (
              <p style={{ ...styles.description, marginTop: '16px' }}>No cross-document pattern found yet. This needs at least two incident/near-miss/audit documents that share a common root cause to detect a genuine pattern.</p>
            )}
          </div>
        )}
      </main>

      <footer style={styles.footer}>
        <p>Industrial Knowledge Intelligence System v1.0 | Backend: {BACKEND_URL}</p>
        <p style={{ fontSize: '11px', marginTop: '8px', opacity: 0.8 }}>Powered by AI retrieval, document intelligence, and operational analytics.</p>
      </footer>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%)',
    fontFamily: '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
    color: '#0f172a'
  },
  header: {
    background: 'linear-gradient(90deg, #0f172a 0%, #1d4ed8 100%)',
    color: 'white',
    padding: '40px 20px 24px',
    textAlign: 'center'
  },
  badge: {
    display: 'inline-block',
    padding: '6px 12px',
    borderRadius: '999px',
    fontSize: '12px',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    backgroundColor: 'rgba(255,255,255,0.16)',
    marginBottom: '10px'
  },
  title: {
    margin: '0 0 10px',
    fontSize: '32px',
    fontWeight: '700'
  },
  subtitle: {
    margin: '0 auto',
    maxWidth: '760px',
    fontSize: '15px',
    lineHeight: 1.6,
    opacity: 0.92
  },
  messageBox: {
    margin: '16px auto 0',
    maxWidth: '760px',
    padding: '10px 12px',
    borderRadius: '8px',
    backgroundColor: 'rgba(255,255,255,0.16)',
    fontSize: '13px'
  },
  nav: {
    display: 'flex',
    gap: '10px',
    padding: '18px 20px',
    backgroundColor: 'white',
    borderBottom: '1px solid #e5e7eb',
    justifyContent: 'center',
    flexWrap: 'wrap'
  },
  navButton: {
    padding: '12px 16px',
    border: '1px solid #dbeafe',
    backgroundColor: 'white',
    cursor: 'pointer',
    borderRadius: '999px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#1e3a8a',
    minHeight: '44px'
  },
  navButtonActive: {
    backgroundColor: '#2563eb',
    color: 'white',
    border: '1px solid #2563eb'
  },
  main: {
    padding: '24px 20px 48px',
    maxWidth: '1200px',
    margin: '0 auto'
  },
  section: {
    backgroundColor: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 12px 30px rgba(15, 23, 42, 0.06)'
  },
  description: {
    color: '#475569',
    lineHeight: 1.6,
    marginTop: '8px'
  },
  kpiGrid: {
    display: 'grid',
    gap: '14px',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    marginTop: '18px'
  },
  kpiCard: {
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    backgroundColor: '#f8fafc'
  },
  architectureCard: {
    marginTop: '18px',
    border: '1px solid #dbeafe',
    backgroundColor: '#eff6ff',
    borderRadius: '12px',
    padding: '16px'
  },
  list: {
    paddingLeft: '18px',
    color: '#1e3a8a',
    lineHeight: 1.7
  },
  queryBox: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    marginTop: '16px'
  },
  queryInput: {
    minHeight: '120px',
    padding: '12px 14px',
    border: '1px solid #cbd5e1',
    borderRadius: '10px',
    resize: 'vertical',
    fontSize: '14px'
  },
  primaryButton: {
    alignSelf: 'flex-start',
    border: 'none',
    borderRadius: '999px',
    padding: '12px 16px',
    backgroundColor: '#2563eb',
    color: 'white',
    cursor: 'pointer',
    fontWeight: '600',
    minHeight: '44px'
  },
  resultBox: {
    marginTop: '18px',
    borderRadius: '12px',
    border: '1px solid #dbeafe',
    backgroundColor: '#f8fbff',
    padding: '16px'
  },
  answerText: {
    marginTop: '8px',
    lineHeight: 1.7,
    color: '#334155'
  },
  confidenceBar: {
    marginTop: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    fontSize: '13px',
    color: '#475569'
  },
  confidenceBarInner: {
    height: '8px',
    backgroundColor: '#2563eb',
    borderRadius: '999px'
  },
  sourcesBox: {
    marginTop: '16px',
    display: 'grid',
    gap: '10px'
  },
  sourceItem: {
    borderTop: '1px solid #e2e8f0',
    paddingTop: '10px'
  },
  sourceExcerpt: {
    marginTop: '4px',
    color: '#64748b',
    fontSize: '13px'
  },
  uploadGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '12px',
    marginTop: '16px'
  },
  uploadCard: {
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    padding: '16px',
    textAlign: 'center',
    backgroundColor: '#f8fafc'
  },
  uploadIcon: {
    fontSize: '28px',
    marginBottom: '8px'
  },
  uploadButton: {
    marginTop: '10px',
    border: 'none',
    borderRadius: '999px',
    padding: '10px 16px',
    backgroundColor: '#0f766e',
    color: 'white',
    cursor: 'pointer',
    minHeight: '44px'
  },
  documentsList: {
    marginTop: '18px',
    display: 'grid',
    gap: '10px'
  },
  documentItem: {
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    padding: '12px 14px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap'
  },
  entityCount: {
    color: '#64748b',
    fontSize: '13px'
  },
  filterBox: {
    marginTop: '16px',
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
    alignItems: 'center'
  },
  label: {
    fontWeight: '600',
    color: '#334155'
  },
  selectInput: {
    padding: '8px 10px',
    borderRadius: '8px',
    border: '1px solid #cbd5e1'
  },
  recsGrid: {
    marginTop: '18px',
    display: 'grid',
    gap: '12px',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))'
  },
  recCard: {
    borderRadius: '12px',
    padding: '16px',
    border: '1px solid #e2e8f0',
    backgroundColor: '#f8fafc'
  },
  highUrgency: {
    borderColor: '#f87171',
    backgroundColor: '#fef2f2'
  },
  mediumUrgency: {
    borderColor: '#f59e0b',
    backgroundColor: '#fffbeb'
  },
  urgencyBadge: {
    marginTop: '8px',
    fontSize: '12px',
    fontWeight: '700',
    color: '#b91c1c'
  },
  evidence: {
    marginTop: '10px',
    display: 'grid',
    gap: '6px',
    fontSize: '13px',
    color: '#475569'
  },
  gapsList: {
    marginTop: '18px',
    display: 'grid',
    gap: '12px'
  },
  gapCard: {
    border: '1px solid #fde68a',
    borderRadius: '12px',
    padding: '16px',
    backgroundColor: '#fffbeb'
  },
  gapHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '8px'
  },
  gapStatus: {
    fontSize: '12px',
    fontWeight: '700',
    color: '#b45309'
  },
  remediationSteps: {
    marginTop: '10px',
    display: 'grid',
    gap: '6px'
  },
  step: {
    color: '#92400e',
    fontSize: '13px'
  },
  secondaryButton: {
    border: '1px solid #2563eb',
    borderRadius: '999px',
    padding: '12px 16px',
    backgroundColor: 'white',
    color: '#2563eb',
    cursor: 'pointer',
    fontWeight: '600',
    minHeight: '44px'
  },
  rcaBox: {
    marginTop: '20px',
    borderRadius: '12px',
    border: '1px solid #ddd6fe',
    backgroundColor: '#faf9ff',
    padding: '18px'
  },
  rcaRow: {
    marginTop: '10px'
  },
  rcaLabel: {
    fontSize: '11px',
    fontWeight: '700',
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    color: '#6d28d9'
  },
  rcaColumns: {
    marginTop: '14px',
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '16px'
  },
  rcaTags: {
    marginTop: '14px',
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px'
  },
  tagProcedure: {
    fontSize: '11.5px',
    backgroundColor: '#eff6ff',
    color: '#1e3a8a',
    padding: '4px 10px',
    borderRadius: '999px'
  },
  tagRegulation: {
    fontSize: '11.5px',
    backgroundColor: '#fdf1e0',
    color: '#92400e',
    padding: '4px 10px',
    borderRadius: '999px'
  },
  lessonCard: {
    border: '1px solid #ddd6fe',
    borderRadius: '12px',
    padding: '16px',
    backgroundColor: '#faf9ff'
  },
  riskBadge: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '3px 10px',
    borderRadius: '999px'
  },
  riskHigh: {
    backgroundColor: '#fee2e2',
    color: '#b91c1c'
  },
  riskMedium: {
    backgroundColor: '#fef3c7',
    color: '#b45309'
  },
  riskLow: {
    backgroundColor: '#d1fae5',
    color: '#15803d'
  },
  footer: {
    textAlign: 'center',
    padding: '18px 20px 28px',
    color: '#64748b',
    fontSize: '13px'
  }
};
