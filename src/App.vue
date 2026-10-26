<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  ArrowUpRight,
  BarChart3,
  Bell,
  BriefcaseBusiness,
  Check,
  ChevronDown,
  FileText,
  GraduationCap,
  LayoutDashboard,
  Moon,
  Search,
  Settings,
  Sparkles,
  Sun,
  Upload,
  UserRound,
  X,
} from 'lucide-vue-next'

const activePage = ref('Dashboard')
const analysisLevel = ref('Standard')
const summaryStyle = ref('Brief')
const selectedFile = ref(null)
const isSampleResume = ref(false)
const isDragging = ref(false)
const fileError = ref('')
const message = ref('')
const searchQuery = ref('')
const fileInput = ref(null)
const maxFileSize = 5 * 1024 * 1024
const isDarkMode = ref(false)
const isBusy = ref(false)
const displayName = ref('Jordan Davis')
const email = ref('jordan.davis@example.com')
const analysisHistory = ref([])
const selectedAnalysis = ref(null)

const sampleResume = {
  name: 'Taylor Reed',
  role: 'Operations Coordinator',
  fileName: 'taylor-reed-sample.txt',
  preview:
    'Fictional professional with experience coordinating schedules, improving team processes, and supporting customer-facing projects.',
  text: `Taylor Reed
Operations Coordinator

Summary
Results-driven operations professional with 4+ years of experience supporting teams, improving workflows, and delivering responsive service to customers and stakeholders. Skilled in scheduling, process documentation, coordinating cross-functional projects, and reducing friction across day-to-day operations.

Experience
Operations Coordinator | BluePeak Studio | 2022 - Present
- Managed calendars, vendor coordination, and internal scheduling for multiple teams.
- Improved onboarding checklists and standard operating procedures to reduce processing delays.
- Supported weekly project reviews with concise status updates and documentation.

Administrative Assistant | Northline Group | 2020 - 2022
- Helped maintain customer records and streamlined communication between departments.
- Prepared recurring reports and tracked project timelines for leadership.

Skills
Project coordination, Microsoft Excel, process improvement, stakeholder support, communication, scheduling, reporting

Education
Bachelor of Arts in Business Administration, State University of Minnesota`,
}

const navigationItems = [
  { label: 'Dashboard', icon: LayoutDashboard },
  { label: 'My Resumes', icon: FileText },
  { label: 'Settings', icon: Settings },
]

const fileName = computed(() => selectedFile.value?.name ?? '')
const fileSize = computed(() => {
  if (!selectedFile.value) return ''
  const size = selectedFile.value.size
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(2)} MB`
})
const hasResumeSelection = computed(() => Boolean(selectedFile.value) || isSampleResume.value)
const initials = computed(
  () =>
    displayName.value
      .trim()
      .split(/\s+/)
      .map((part) => part[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() || 'JD',
)
const filteredResumes = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return analysisHistory.value
  return analysisHistory.value.filter((resume) => resume.filename.toLowerCase().includes(query))
})
const dashboardStats = computed(() => {
  const latest = analysisHistory.value[0]
  return {
    total: analysisHistory.value.length,
    lastAnalyzed: latest ? latest.completedAt : 'No analyses yet',
    skillsCount: selectedAnalysis.value?.skills?.length ?? latest?.skills?.length ?? 0,
    completeness: selectedAnalysis.value?.completeness ?? latest?.completeness ?? 0,
  }
})

function navigateTo(page) {
  activePage.value = page
  message.value = ''
}

function openFilePicker() {
  fileInput.value?.click()
}

function chooseFile(file) {
  if (!file) return

  message.value = ''
  fileError.value = ''
  const extension = file.name.toLowerCase().match(/\.([^.]+)$/)?.[1]
  const mimeType = file.type.toLowerCase()
  const isPdf = extension === 'pdf' && (!mimeType || ['application/pdf', 'application/x-pdf'].includes(mimeType))
  const isText = extension === 'txt' && (!mimeType || mimeType === 'text/plain')

  if (!isPdf && !isText) {
    selectedFile.value = null
    isSampleResume.value = false
    fileError.value = 'Unsupported file type. Choose a PDF or TXT file.'
    return
  }

  if (file.size > maxFileSize) {
    selectedFile.value = null
    isSampleResume.value = false
    fileError.value = 'This file is larger than 5 MB. Choose a smaller PDF or TXT file.'
    return
  }

  selectedFile.value = file
  isSampleResume.value = false
  selectedAnalysis.value = null
}

function chooseSampleResume() {
  selectedFile.value = null
  isSampleResume.value = true
  fileError.value = ''
  message.value = ''
  selectedAnalysis.value = null
}

function clearSelection() {
  selectedFile.value = null
  isSampleResume.value = false
  selectedAnalysis.value = null
  fileError.value = ''
  message.value = ''
}

function onFileChange(event) {
  chooseFile(event.target.files?.[0])
  event.target.value = ''
}

function onDrop(event) {
  isDragging.value = false
  chooseFile(event.dataTransfer?.files?.[0])
}

function preventFileNavigation(event) {
  if (Array.from(event.dataTransfer?.types ?? []).includes('Files')) {
    event.preventDefault()
  }
}

async function analyzeResume() {
  if (!hasResumeSelection.value) return

  if (!isSampleResume.value && !selectedFile.value) {
    fileError.value = 'Choose a PDF or TXT resume before analyzing.'
    return
  }

  isBusy.value = true
  fileError.value = ''
  message.value = ''
  selectedAnalysis.value = null

  try {
    let filename = sampleResume.fileName
    let text = sampleResume.text

    if (!isSampleResume.value) {
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      const extractionResponse = await fetch('/api/resumes/extract', {
        method: 'POST',
        body: formData,
      })
      const extraction = await extractionResponse.json().catch(() => ({}))
      if (!extractionResponse.ok) {
        throw new Error(extraction.detail || 'The backend could not extract text from this resume.')
      }
      filename = extraction.filename
      text = extraction.text
    }

    const response = await fetch('/api/resumes/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename,
        text,
        analysis_level: analysisLevel.value,
        summary_style: summaryStyle.value,
      }),
    })

    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((issue) => issue.msg).join(' ')
        : data.detail
      throw new Error(detail || 'The backend could not analyze this resume.')
    }

    const analysisResult = {
      ...data,
      completedAt: new Date().toLocaleString(),
    }

    selectedAnalysis.value = analysisResult
    if (!isSampleResume.value) {
      analysisHistory.value = [analysisResult, ...analysisHistory.value.filter((resume) => resume.filename !== analysisResult.filename)].slice(0, 8)
    }
    message.value = analysisResult.message || 'Resume analyzed successfully.'
  } catch (error) {
    fileError.value =
      error instanceof TypeError
        ? 'Could not reach the backend. Make sure it is running on port 8000, then try again.'
        : error.message || 'Unable to analyze this resume right now.'
    message.value = 'Retry the analysis to try again.'
  } finally {
    isBusy.value = false
  }
}

function saveSettings() {
  message.value = 'Settings saved in this page’s frontend state. They are not stored permanently.'
}

onMounted(() => {
  window.addEventListener('dragover', preventFileNavigation)
  window.addEventListener('drop', preventFileNavigation)
})

onBeforeUnmount(() => {
  window.removeEventListener('dragover', preventFileNavigation)
  window.removeEventListener('drop', preventFileNavigation)
})
</script>

<template>
  <div class="app-shell" :class="{ 'dark-theme': isDarkMode }">
    <aside class="sidebar">
      <button class="brand" type="button" aria-label="ResumeIQ dashboard" @click="navigateTo('Dashboard')">
        <span class="brand-mark"><FileText :size="19" :stroke-width="2.2" /></span>
        <span>Resume<span class="brand-accent">IQ</span></span>
      </button>

      <nav class="primary-nav" aria-label="Main navigation">
        <button
          v-for="item in navigationItems"
          :key="item.label"
          class="nav-item"
          :class="{ 'nav-item-active': activePage === item.label }"
          type="button"
          :aria-current="activePage === item.label ? 'page' : undefined"
          @click="navigateTo(item.label)"
        >
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-bottom">
        <div class="upgrade-card">
          <div class="upgrade-icon"><Sparkles :size="16" /></div>
          <p class="upgrade-title">Make every application count</p>
          <p class="upgrade-copy">Get clear, useful insights from your resume.</p>
          <button type="button" class="upgrade-link" @click="navigateTo('Dashboard')">
            Explore ResumeIQ <ArrowUpRight :size="14" />
          </button>
        </div>
        <button class="user-card" type="button" @click="navigateTo('Settings')">
          <span class="avatar avatar-small">{{ initials }}</span>
          <span class="user-info">
            <span class="user-name">{{ displayName }}</span>
            <span class="user-plan">Local workspace</span>
          </span>
          <ChevronDown :size="16" class="user-chevron" />
        </button>
      </div>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div class="breadcrumb">
          <span>ResumeIQ</span>
          <span class="breadcrumb-slash">/</span>
          <strong>{{ activePage }}</strong>
        </div>

        <div class="topbar-actions">
          <button class="icon-button" type="button" aria-label="Notifications" @click="message = 'You are all caught up.'">
            <Bell :size="18" />
            <span class="notification-dot"></span>
          </button>
          <span class="topbar-divider"></span>
          <button class="profile-button" type="button" @click="navigateTo('Settings')">
            <span class="avatar">{{ initials }}</span>
            <span class="profile-name">{{ displayName }}</span>
            <ChevronDown :size="15" />
          </button>
        </div>
      </header>

      <div class="page-content">
        <div v-if="message" class="status-message" role="status" aria-live="polite">
          <span>{{ message }}</span>
          <button type="button" aria-label="Dismiss message" @click="message = ''"><X :size="16" /></button>
        </div>

        <template v-if="activePage === 'Dashboard'">
          <section class="welcome-section">
            <div>
              <div class="eyebrow"><span class="eyebrow-dot"></span> YOUR RESUME WORKSPACE</div>
              <h1>Welcome to ResumeIQ</h1>
              <p class="welcome-copy">Analyze resumes, review key strengths, and prepare for the next opportunity.</p>
            </div>
            <div class="welcome-note">
              <div class="welcome-note-icon"><Sparkles :size="17" /></div>
              <span>Thoughtful insights start with<br /><strong>your experience.</strong></span>
            </div>
          </section>

          <section class="dashboard-grid">
            <div class="dashboard-analysis">
              <section class="card upload-card">
                <div class="section-heading">
                  <div class="heading-icon indigo-icon"><Upload :size="18" /></div>
                  <div>
                    <h2>Upload your resume</h2>
                    <p>Start with a PDF or TXT file</p>
                  </div>
                  <span class="step-badge">STEP 1</span>
                </div>

                <div
                  class="drop-zone"
                  :class="{ 'drop-zone-active': isDragging, 'drop-zone-selected': selectedFile || isSampleResume }"
                  @dragenter.prevent="isDragging = true"
                  @dragover.prevent="isDragging = true"
                  @dragleave.prevent="isDragging = false"
                  @drop.prevent="onDrop"
                >
                  <template v-if="selectedFile">
                    <div class="upload-symbol upload-symbol-success"><Check :size="21" /></div>
                    <strong class="drop-title">{{ fileName }}</strong>
                    <span class="drop-hint">{{ fileSize }} · File selected</span>
                    <button class="text-button replace-button" type="button" @click="openFilePicker">Choose a different file</button>
                  </template>
                  <template v-else-if="isSampleResume">
                    <div class="upload-symbol upload-symbol-success"><FileText :size="21" /></div>
                    <strong class="drop-title">{{ sampleResume.name }}</strong>
                    <span class="drop-hint">{{ sampleResume.role }}</span>
                    <span class="sample-status">Fictional sample · not stored in history</span>
                    <p class="sample-preview">{{ sampleResume.preview }}</p>
                    <button class="text-button replace-button" type="button" @click="openFilePicker">Choose a real file</button>
                  </template>
                  <template v-else>
                    <div class="upload-symbol"><Upload :size="21" /></div>
                    <strong class="drop-title">Drop your resume here</strong>
                    <span class="drop-hint">or browse files from your device</span>
                    <button class="browse-button" type="button" @click="openFilePicker">Choose a file</button>
                    <span class="file-note">PDF or TXT · Up to 5 MB</span>
                  </template>
                </div>

                <div v-if="selectedFile" class="selection-actions">
                  <button class="text-button remove-button" type="button" @click="clearSelection">Remove file</button>
                </div>

                <p v-if="fileError" class="file-error" role="alert" aria-live="assertive">{{ fileError }}</p>
                <div class="privacy-note">
                  <span class="privacy-check"><Check :size="12" /></span>
                  Files stay in memory only while this page is open.
                  <button class="sample-button" type="button" @click="chooseSampleResume">Try Sample Resume</button>
                </div>
              </section>

              <section class="card options-card">
                <div class="section-heading options-heading">
                  <div class="heading-icon slate-icon"><Settings :size="18" /></div>
                  <div>
                    <h2>Analysis preferences</h2>
                    <p>Choose how detailed your insights should be</p>
                  </div>
                  <span class="step-badge">STEP 2</span>
                </div>

                <fieldset class="option-group">
                  <legend>Analysis level</legend>
                  <div class="segmented-control">
                    <button
                      v-for="option in ['Basic', 'Standard', 'Detailed']"
                      :key="option"
                      type="button"
                      :aria-pressed="analysisLevel === option"
                      :class="{ 'segment-active': analysisLevel === option }"
                      @click="analysisLevel = option"
                    >{{ option }}</button>
                  </div>
                </fieldset>

                <fieldset class="option-group summary-options">
                  <legend>Summary style</legend>
                  <div class="style-options">
                    <button
                      v-for="option in [
                        { label: 'Brief', description: 'Quick overview', icon: FileText },
                        { label: 'Detailed', description: 'More context', icon: BarChart3 },
                        { label: 'Bullet Points', description: 'Easy to scan', icon: Check },
                      ]"
                      :key="option.label"
                      type="button"
                      class="style-option"
                      :class="{ 'style-option-active': summaryStyle === option.label }"
                      :aria-pressed="summaryStyle === option.label"
                      @click="summaryStyle = option.label"
                    >
                      <component :is="option.icon" :size="16" />
                      <span><strong>{{ option.label }}</strong><small>{{ option.description }}</small></span>
                      <span class="radio-indicator"><span></span></span>
                    </button>
                  </div>
                </fieldset>

                <button class="analyze-button" type="button" :disabled="!hasResumeSelection || isBusy" @click="analyzeResume">
                  <span v-if="isBusy" class="spinner"></span>
                  <Sparkles :size="17" v-if="!isBusy" />
                  {{ isBusy ? 'Analyzing...' : 'Analyze Resume' }}
                  <ArrowUpRight :size="16" class="analyze-arrow" />
                </button>
                <p class="backend-note">Uploaded resumes are analyzed by the backend. Try the sample resume to preview demo results.</p>
              </section>
            </div>

            <div class="dashboard-results">
              <section class="results-intro">
                <div>
                  <div class="eyebrow results-eyebrow">LIVE OVERVIEW</div>
                  <h2>Resume insights</h2>
                </div>
                <span class="preview-badge"><span></span> ANALYSIS</span>
              </section>

              <section v-if="selectedAnalysis" class="card result-card summary-card">
                <div class="result-title-group">
                  <div class="heading-icon indigo-icon"><Sparkles :size="17" /></div>
                  <div>
                    <h3>Summary</h3>
                    <p>{{ selectedAnalysis.filename }}</p>
                  </div>
                  <span class="analysis-mode-badge" :class="{ 'demo-mode-badge': selectedAnalysis.analysis_status === 'demo_mode' }">
                    {{ selectedAnalysis.analysis_status === 'demo_mode' ? 'DEMO MODE' : 'GEMINI AI' }}
                  </span>
                </div>
                <p v-if="selectedAnalysis.candidate_name" class="candidate-name">{{ selectedAnalysis.candidate_name }}</p>
                <p v-if="selectedAnalysis.contact_details?.length" class="candidate-contact">{{ selectedAnalysis.contact_details.join(' · ') }}</p>
                <p class="analysis-summary">{{ selectedAnalysis.summary }}</p>
              </section>

              <div v-else class="card result-card summary-card empty-card">
                <div class="result-title-group">
                  <div class="heading-icon indigo-icon"><Sparkles :size="17" /></div>
                  <div>
                    <h3>Summary</h3>
                    <p>Professional profile overview</p>
                  </div>
                </div>
                <div class="empty-summary">
                  <div class="empty-icon"><FileText :size="18" /></div>
                  <p>Summary will appear here after you analyze a resume.</p>
                </div>
              </div>

              <div class="dashboard-insights">
                <section class="card result-card insight-card">
                  <div class="result-title-group">
                    <div class="heading-icon green-icon"><BarChart3 :size="17" /></div>
                    <div>
                      <h3>Extracted skills</h3>
                      <p>Skills identified in the resume</p>
                    </div>
                  </div>
                  <div v-if="selectedAnalysis?.skills?.length" class="skill-groups">
                    <div v-if="selectedAnalysis.technical_skills?.length">
                      <strong>Technical</strong>
                      <div class="chip-list">
                        <span v-for="skill in selectedAnalysis.technical_skills" :key="`technical-${skill}`" class="skill-chip">{{ skill }}</span>
                      </div>
                    </div>
                    <div v-if="selectedAnalysis.soft_skills?.length">
                      <strong>Soft skills</strong>
                      <div class="chip-list">
                        <span v-for="skill in selectedAnalysis.soft_skills" :key="`soft-${skill}`" class="skill-chip">{{ skill }}</span>
                      </div>
                    </div>
                  </div>
                  <p v-else class="placeholder-copy">No skills extracted yet.</p>
                </section>

                <section class="card result-card insight-card">
                  <div class="result-title-group">
                    <div class="heading-icon blue-icon"><GraduationCap :size="17" /></div>
                    <div>
                      <h3>Education</h3>
                      <p>Education history</p>
                    </div>
                  </div>
                  <ul v-if="selectedAnalysis?.education?.length" class="detail-list">
                    <li v-for="item in selectedAnalysis.education" :key="item">{{ item }}</li>
                  </ul>
                  <p v-else class="placeholder-copy">Education details will appear here.</p>
                </section>

                <section class="card result-card insight-card">
                  <div class="result-title-group">
                    <div class="heading-icon slate-icon"><BriefcaseBusiness :size="17" /></div>
                    <div>
                      <h3>Internships &amp; work</h3>
                      <p>Professional experience</p>
                    </div>
                  </div>
                  <template v-if="selectedAnalysis?.experience?.length">
                    <strong v-if="selectedAnalysis.internships?.length" class="detail-label">Internships</strong>
                    <ul v-if="selectedAnalysis.internships?.length" class="detail-list">
                      <li v-for="item in selectedAnalysis.internships" :key="`internship-${item}`">{{ item }}</li>
                    </ul>
                    <strong v-if="selectedAnalysis.work_experience?.length" class="detail-label">Work experience</strong>
                    <ul v-if="selectedAnalysis.work_experience?.length" class="detail-list">
                      <li v-for="item in selectedAnalysis.work_experience" :key="`work-${item}`">{{ item }}</li>
                    </ul>
                  </template>
                  <p v-else class="placeholder-copy">Experience details will appear here.</p>
                </section>

                <section class="card result-card insight-card">
                  <div class="result-title-group">
                    <div class="heading-icon amber-icon"><Check :size="17" /></div>
                    <div>
                      <h3>Completeness</h3>
                      <p>Resume sections</p>
                    </div>
                  </div>
                  <div v-if="selectedAnalysis?.completeness !== undefined && selectedAnalysis?.completeness !== null" class="completeness-row">
                    <span class="completeness-ring"><span>{{ selectedAnalysis.completeness }}</span></span>
                    <div>
                      <strong>Resume coverage</strong>
                      <small>Strong content coverage for screening.</small>
                    </div>
                  </div>
                  <div v-else class="completeness-empty">
                    <span class="completeness-ring"><span>—</span></span>
                    <div>
                      <strong>Not calculated</strong>
                      <small>No score is available.</small>
                    </div>
                  </div>
                </section>
              </div>

              <section v-if="selectedAnalysis" class="analysis-details-grid">
                <section class="card result-card insight-card">
                  <div class="result-title-group">
                    <div class="heading-icon blue-icon"><FileText :size="17" /></div>
                    <div><h3>Projects</h3><p>Projects identified in the resume</p></div>
                  </div>
                  <ul v-if="selectedAnalysis.projects?.length" class="detail-list">
                    <li v-for="item in selectedAnalysis.projects" :key="item">{{ item }}</li>
                  </ul>
                  <p v-else class="placeholder-copy">No projects found.</p>
                </section>
                <section class="card result-card insight-card">
                  <div class="result-title-group">
                    <div class="heading-icon amber-icon"><Check :size="17" /></div>
                    <div><h3>Certifications &amp; achievements</h3><p>Credentials and recognition</p></div>
                  </div>
                  <ul v-if="selectedAnalysis.certifications?.length || selectedAnalysis.achievements?.length" class="detail-list">
                    <li v-for="item in selectedAnalysis.certifications" :key="`cert-${item}`">{{ item }}</li>
                    <li v-for="item in selectedAnalysis.achievements" :key="`achievement-${item}`">{{ item }}</li>
                  </ul>
                  <p v-else class="placeholder-copy">No certifications or achievements found.</p>
                </section>
                <section class="card result-card insight-card">
                  <div class="result-title-group">
                    <div class="heading-icon slate-icon"><Search :size="17" /></div>
                    <div><h3>Missing information</h3><p>Details not found by analysis</p></div>
                  </div>
                  <ul v-if="selectedAnalysis.missing_information?.length" class="detail-list">
                    <li v-for="item in selectedAnalysis.missing_information" :key="item">{{ item }}</li>
                  </ul>
                  <p v-else class="placeholder-copy">No obvious missing information found.</p>
                </section>
                <section class="card result-card insight-card">
                  <div class="result-title-group">
                    <div class="heading-icon green-icon"><Sparkles :size="17" /></div>
                    <div><h3>Improvement suggestions</h3><p>Ways to strengthen the resume</p></div>
                  </div>
                  <ul v-if="selectedAnalysis.improvement_suggestions?.length" class="detail-list">
                    <li v-for="item in selectedAnalysis.improvement_suggestions" :key="item">{{ item }}</li>
                  </ul>
                  <p v-else class="placeholder-copy">No suggestions returned.</p>
                </section>
              </section>

              <section class="card recent-card">
                <div class="recent-header">
                  <div>
                    <h2>Recent resumes</h2>
                    <p>Real analyses in this browser session</p>
                  </div>
                  <button class="text-button" type="button" @click="navigateTo('My Resumes')">View all</button>
                </div>
                <div v-if="analysisHistory.length" class="recent-list">
                  <div v-for="resume in analysisHistory.slice(0, 3)" :key="resume.filename + resume.completedAt" class="recent-item">
                    <span class="recent-file-icon"><FileText :size="15" /></span>
                    <span class="recent-name">{{ resume.filename }}<small>{{ resume.completedAt }}</small></span>
                    <span class="status-chip">Analyzed</span>
                  </div>
                </div>
                <p v-else class="recent-empty">No saved analyses yet. Upload a file and analyze it.</p>
              </section>
            </div>
          </section>
        </template>

        <template v-else-if="activePage === 'My Resumes'">
          <section class="page-heading">
            <div>
              <div class="eyebrow">YOUR FILE LIBRARY</div>
              <h1>My Resumes</h1>
              <p class="welcome-copy">Search and review resume analyses completed in this browser session.</p>
            </div>
            <button class="add-resume-button" type="button" @click="openFilePicker"><Upload :size="16" /> Add resume</button>
          </section>

          <section class="card resume-library">
            <div class="library-toolbar">
              <label class="search-box">
                <Search :size="17" />
                <input v-model="searchQuery" type="search" placeholder="Search analyses" aria-label="Search resumes by name" />
              </label>
              <span class="session-note">Stored in memory only · cleared when you close the page</span>
            </div>

            <div v-if="filteredResumes.length" class="resume-table-wrap">
              <table class="resume-table">
                <thead>
                  <tr>
                    <th scope="col">Resume name</th>
                    <th scope="col">File type</th>
                    <th scope="col">Analyzed</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="resume in filteredResumes" :key="resume.filename + resume.completedAt">
                    <td>
                      <span class="table-file">
                        <span class="recent-file-icon"><FileText :size="15" /></span>
                        <strong>{{ resume.filename }}</strong>
                      </span>
                    </td>
                    <td>{{ resume.file_type || 'TXT' }}</td>
                    <td>{{ resume.completedAt || 'Unknown' }}</td>
                    <td><span class="status-chip">Analyzed</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="library-empty">
              <div class="empty-icon"><FileText :size="20" /></div>
              <h2>{{ searchQuery ? 'No matching analyses' : 'No analyses saved yet' }}</h2>
              <p>{{ searchQuery ? 'Try another name or clear your search.' : 'Upload a resume and run an analysis to build your file history.' }}</p>
              <button v-if="!searchQuery" class="browse-button" type="button" @click="openFilePicker">Add your first resume</button>
            </div>
          </section>
        </template>

        <template v-else>
          <section class="page-heading">
            <div>
              <div class="eyebrow">PERSONALIZE YOUR WORKSPACE</div>
              <h1>Settings</h1>
              <p class="welcome-copy">Manage preferences for this ResumeIQ session.</p>
            </div>
          </section>

          <div class="settings-layout">
            <section class="card settings-card">
              <div class="settings-card-heading">
                <div class="heading-icon blue-icon"><UserRound :size="18" /></div>
                <div>
                  <h2>Profile</h2>
                  <p>Demo profile details shown in this workspace</p>
                </div>
              </div>
              <div class="form-grid">
                <label class="form-field"><span>Display name</span><input v-model="displayName" type="text" autocomplete="name" /></label>
                <label class="form-field"><span>Email address</span><input v-model="email" type="email" autocomplete="email" /></label>
              </div>
            </section>

            <section class="card settings-card">
              <div class="settings-card-heading">
                <div class="heading-icon indigo-icon"><Sun v-if="!isDarkMode" :size="18" /><Moon v-else :size="18" /></div>
                <div>
                  <h2>Appearance</h2>
                  <p>Choose the theme for this page</p>
                </div>
              </div>
              <label class="toggle-row">
                <span><strong>{{ isDarkMode ? 'Dark mode' : 'Light mode' }}</strong><small>Applied immediately in this browser session.</small></span>
                <input v-model="isDarkMode" type="checkbox" role="switch" aria-label="Toggle dark mode" />
                <span class="toggle-track" aria-hidden="true"></span>
              </label>
            </section>

            <section class="card settings-card">
              <div class="settings-card-heading">
                <div class="heading-icon slate-icon"><Settings :size="18" /></div>
                <div>
                  <h2>Analysis preferences</h2>
                  <p>Defaults used by the dashboard controls</p>
                </div>
              </div>
              <div class="form-grid">
                <label class="form-field"><span>Default analysis level</span><select v-model="analysisLevel"><option>Basic</option><option>Standard</option><option>Detailed</option></select></label>
                <label class="form-field"><span>Default summary style</span><select v-model="summaryStyle"><option>Brief</option><option>Detailed</option><option>Bullet Points</option></select></label>
              </div>
            </section>

            <section class="card settings-card file-settings">
              <div class="settings-card-heading">
                <div class="heading-icon green-icon"><Upload :size="18" /></div>
                <div>
                  <h2>File uploads</h2>
                  <p>Current frontend validation rules</p>
                </div>
              </div>
              <div class="upload-limits">
                <span><strong>Accepted formats</strong><small>PDF and TXT</small></span>
                <span><strong>Maximum file size</strong><small>5 MB per file</small></span>
              </div>
            </section>
          </div>

          <div class="settings-actions">
            <span>Settings are held in frontend state and are not saved to a server.</span>
            <button class="analyze-button save-button" type="button" @click="saveSettings"><Check :size="16" /> Save Settings</button>
          </div>
        </template>

        <input
          ref="fileInput"
          class="visually-hidden"
          type="file"
          accept=".pdf,.txt,application/pdf,text/plain"
          aria-label="Choose a PDF or TXT resume"
          :aria-invalid="Boolean(fileError)"
          :aria-describedby="fileError ? 'file-error' : undefined"
          @change="onFileChange"
        />
      </div>
    </main>
  </div>
</template>
