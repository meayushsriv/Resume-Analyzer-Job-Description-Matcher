import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')

  const [resumeId, setResumeId] = useState('')
  const [status, setStatus] = useState('')
  const [statusError, setStatusError] = useState('')

  const [resumeData, setResumeData] = useState(null)
  const [loadingResume, setLoadingResume] = useState(false)

  const [matchForm, setMatchForm] = useState({
    title: '',
    company: '',
    location: '',
    description: '',
  })
  const [matching, setMatching] = useState(false)
  const [matchResult, setMatchResult] = useState(null)
  const [matchError, setMatchError] = useState('')

  // Poll status every few seconds while processing
  useEffect(() => {
    if (!resumeId || !status || ['completed', 'failed'].includes(status)) {
      return undefined
    }

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/resumes/${resumeId}/status`)
        if (!res.ok) {
          // 404/400 etc.
          const text = await res.text()
          setStatusError(`Status check failed (${res.status}): ${text}`)
          clearInterval(interval)
          return
        }
        const json = await res.json()
        setStatus(json.status)

        if (json.status === 'completed') {
          clearInterval(interval)
          await fetchResume(resumeId)
        }
      } catch (err) {
        setStatusError(`Status check error: ${err instanceof Error ? err.message : String(err)}`)
        clearInterval(interval)
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [resumeId, status])

  const onFileChange = (event) => {
    setFile(event.target.files?.[0] ?? null)
    setUploadError('')
  }

  const handleUpload = async (event) => {
    event.preventDefault()
    if (!file) {
      setUploadError('Please select a resume file to upload.')
      return
    }

    setUploading(true)
    setUploadError('')
    setStatusError('')
    setResumeData(null)
    setMatchResult(null)
    setMatchError('')

    try {
      const formData = new FormData()
      // Backend expects parameter name `file`
      formData.append('file', file)

      const res = await fetch('/api/v1/resumes/upload', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Upload failed (${res.status}): ${text}`)
      }

      const json = await res.json()
      setResumeId(json.id)
      setStatus(json.status)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err))
    } finally {
      setUploading(false)
    }
  }

  const fetchResume = async (id) => {
    setLoadingResume(true)
    try {
      const res = await fetch(`/api/v1/resumes/${id}`)
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Failed to fetch resume (${res.status}): ${text}`)
      }
      const json = await res.json()
      setResumeData(json)
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoadingResume(false)
    }
  }

  const handleMatchChange = (event) => {
    const { name, value } = event.target
    setMatchForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleMatchSubmit = async (event) => {
    event.preventDefault()
    if (!resumeId) {
      setMatchError('Upload and process a resume first.')
      return
    }
    setMatching(true)
    setMatchError('')

    try {
      const payload = {
        jobDescription: {
          title: matchForm.title || undefined,
          company: matchForm.company || undefined,
          location: matchForm.location || undefined,
          description: matchForm.description || undefined,
        },
        options: {
          includeExplanation: true,
          detailedBreakdown: true,
          suggestImprovements: true,
        },
      }

      const res = await fetch(`/api/v1/resumes/${resumeId}/match`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Match request failed (${res.status}): ${text}`)
      }

      const json = await res.json()
      setMatchResult(json)
    } catch (err) {
      setMatchError(err instanceof Error ? err.message : String(err))
    } finally {
      setMatching(false)
    }
  }

  return (
    <>
      <section id="center">
        <div>
          <h1>AI-Powered Resume Parser</h1>
          <p>Upload a resume, track processing, view structured data, and match against a job description.</p>
        </div>
        <form className="card" onSubmit={handleUpload}>
          <label className="field">
            <span>Resume file (PDF, DOCX, TXT, image)</span>
            <input type="file" onChange={onFileChange} />
          </label>
          <button type="submit" className="primary" disabled={uploading}>
            {uploading ? 'Uploading…' : 'Upload & Start Parsing'}
          </button>
          {uploadError && <p className="error">{uploadError}</p>}
          {resumeId && (
            <p className="meta">
              Current resume ID: <code>{resumeId}</code>
            </p>
          )}
        </form>

        {resumeId && (
          <div className="card">
            <h2>Processing Status</h2>
            <p>
              Status:{' '}
              <strong>
                {status || 'pending'}
                {status && !['completed', 'failed'].includes(status) ? ' (polling…)' : ''}
              </strong>
            </p>
            {statusError && <p className="error">{statusError}</p>}
            {loadingResume && <p>Loading parsed resume…</p>}
          </div>
        )}

        {resumeData && (
          <div className="card">
            <h2>Parsed Resume JSON</h2>
            <pre className="json-view">
              {JSON.stringify(resumeData, null, 2)}
            </pre>
          </div>
        )}

        <div className="card">
          <h2>Match Against Job Description</h2>
          <form onSubmit={handleMatchSubmit} className="match-form">
            <div className="field">
              <label htmlFor="title">Job title</label>
              <input
                id="title"
                name="title"
                value={matchForm.title}
                onChange={handleMatchChange}
                placeholder="e.g. Senior Backend Engineer"
              />
            </div>
            <div className="field">
              <label htmlFor="company">Company</label>
              <input
                id="company"
                name="company"
                value={matchForm.company}
                onChange={handleMatchChange}
                placeholder="e.g. Acme Corp"
              />
            </div>
            <div className="field">
              <label htmlFor="location">Location</label>
              <input
                id="location"
                name="location"
                value={matchForm.location}
                onChange={handleMatchChange}
                placeholder="e.g. Remote / Bangalore"
              />
            </div>
            <div className="field">
              <label htmlFor="description">Job description</label>
              <textarea
                id="description"
                name="description"
                rows={4}
                value={matchForm.description}
                onChange={handleMatchChange}
                placeholder="Paste the full job description here…"
              />
            </div>
            <button type="submit" className="primary" disabled={matching}>
              {matching ? 'Matching…' : 'Run Match Analysis'}
            </button>
            {matchError && <p className="error">{matchError}</p>}
          </form>
        </div>

        {matchResult && (
          <div className="card">
            <h2>Match Result</h2>
            <pre className="json-view">
              {JSON.stringify(matchResult, null, 2)}
            </pre>
          </div>
        )}
      </section>
    </>
  )
}

export default App
