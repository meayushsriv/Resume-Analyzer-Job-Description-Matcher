# Location: /src/api/v1/schemas.py

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime
import uuid

# -------------------------------------------------
# 1. SCHEMAS FOR THE 'GET /resumes/{id}' RESPONSE
# -------------------------------------------------

class ResumeMetadata(BaseModel):
    fileName: str
    fileSize: int
    uploadedAt: datetime
    processedAt: Optional[datetime] = None
    processingTime: Optional[float] = None

class PersonalInfoName(BaseModel):
    first: Optional[str] = None
    last: Optional[str] = None
    full: Optional[str] = None

class PersonalInfoContactAddress(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    country: Optional[str] = None

class PersonalInfoContact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[PersonalInfoContactAddress] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None

class PersonalInfo(BaseModel):
    name: Optional[PersonalInfoName] = None
    contact: Optional[PersonalInfoContact] = None

class Summary(BaseModel):
    text: Optional[str] = None
    careerLevel: Optional[str] = None
    industryFocus: Optional[str] = None

class Experience(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    current: Optional[bool] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    achievements: Optional[List[str]] = []
    technologies: Optional[List[str]] = []

class Education(BaseModel):
    degree: Optional[str] = None
    field: Optional[str] = None
    institution: Optional[str] = None
    location: Optional[str] = None
    graduationDate: Optional[str] = None
    gpa: Optional[float] = None
    honors: Optional[List[str]] = []

class SkillCategory(BaseModel):
    category: str
    items: List[str]

class SkillLanguage(BaseModel):
    language: str
    proficiency: str

class Skills(BaseModel):
    technical: Optional[List[SkillCategory]] = []
    soft: Optional[List[str]] = []
    languages: Optional[List[SkillLanguage]] = []

class Certification(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    issueDate: Optional[str] = None
    expiryDate: Optional[str] = None
    credentialId: Optional[str] = None

class AIEnhancements(BaseModel):
    qualityScore: Optional[int] = None
    completenessScore: Optional[int] = None
    suggestions: Optional[List[str]] = []
    industryFit: Optional[Dict[str, float]] = {}
    careerProgressionAnalysis: Optional[str] = None

class ResumeDataResponse(BaseModel):
    """
    The main response model for the GET /resumes/{id} endpoint.
    """
    id: uuid.UUID
    metadata: ResumeMetadata
    personalInfo: Optional[PersonalInfo] = None
    summary: Optional[Summary] = None
    experience: Optional[List[Experience]] = []
    education: Optional[List[Education]] = []
    skills: Optional[Skills] = None
    certifications: Optional[List[Certification]] = []
    aiEnhancements: Optional[AIEnhancements] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------
# 2. SCHEMAS FOR THE 'POST /resumes/{id}/match' ENDPOINT
# -------------------------------------------------

# --- JOB DESCRIPTION (INPUT) ---

class JobExperience(BaseModel):
    minimum: Optional[int] = None
    preferred: Optional[int] = None
    level: Optional[str] = None

class JobRequirements(BaseModel):
    required: Optional[List[str]] = []
    preferred: Optional[List[str]] = []

class JobSkills(BaseModel):
    required: Optional[List[str]] = []
    preferred: Optional[List[str]] = []

class JobSalary(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None
    currency: Optional[str] = None

class JobDescription(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    experience: Optional[JobExperience] = None
    description: Optional[str] = None
    requirements: Optional[JobRequirements] = None
    skills: Optional[JobSkills] = None
    salary: Optional[JobSalary] = None
    benefits: Optional[List[str]] = []
    industry: Optional[str] = None

class MatchOptions(BaseModel):
    includeExplanation: bool = True
    detailedBreakdown: bool = True
    suggestImprovements: bool = True

class MatchRequest(BaseModel):
    jobDescription: JobDescription
    options: Optional[MatchOptions] = None


# --- MATCH RESPONSE (OUTPUT) ---
# --- THIS IS THE FULLY-CORRECTED, EXPLICIT SCHEMA ---

class SkillsMatchDetails_Details(BaseModel):
    requiredSkillsMatched: int
    totalRequiredSkills: int
    preferredSkillsMatched: int
    totalPreferredSkills: int
    matchedSkills: List[str]
    missingRequired: List[str]
    missingPreferred: List[str]

class SkillsMatchDetails(BaseModel):
    score: int
    weight: int
    details: SkillsMatchDetails_Details

class ExperienceMatchDetails_Details(BaseModel):
    candidateExperience: float
    requiredExperience: int
    preferredExperience: int
    levelMatch: str
    industryMatch: bool

class ExperienceMatchDetails(BaseModel):
    score: int
    weight: int
    details: ExperienceMatchDetails_Details

class EducationMatchDetails_Details(BaseModel):
    meetsRequirements: bool
    exceedsRequirements: bool
    fieldRelevance: str
    institutionPrestige: str

class EducationMatchDetails(BaseModel):
    score: int
    weight: int
    details: EducationMatchDetails_Details

class RoleAlignmentDetails_Details(BaseModel):
    titleSimilarity: float
    responsibilityOverlap: float
    careerProgression: str

class RoleAlignmentDetails(BaseModel):
    score: int
    weight: int
    details: RoleAlignmentDetails_Details

class LocationMatchDetails_Details(BaseModel):
    currentLocation: str
    jobLocation: str
    relocationRequired: bool

class LocationMatchDetails(BaseModel):
    score: int
    weight: int
    details: LocationMatchDetails_Details

class CategoryScores(BaseModel):
    skillsMatch: SkillsMatchDetails
    experienceMatch: ExperienceMatchDetails
    educationMatch: EducationMatchDetails
    roleAlignment: RoleAlignmentDetails
    locationMatch: LocationMatchDetails

class GapAnalysisItem(BaseModel):
    category: str
    missing: Any
    impact: str
    suggestion: str

class GapAnalysis(BaseModel):
    criticalGaps: List[GapAnalysisItem]
    improvementAreas: List[GapAnalysisItem]

class SalaryAlignment(BaseModel):
    candidateExpectation: str
    jobSalaryRange: str
    marketRate: str
    alignment: str

class MatchingResults(BaseModel):
    overallScore: int
    confidence: float
    recommendation: str
    categoryScores: CategoryScores
    strengthAreas: List[str]
    gapAnalysis: GapAnalysis # <-- Was Dict, now a proper schema
    salaryAlignment: SalaryAlignment
    competitiveAdvantages: List[str]

class MatchExplanation(BaseModel):
    summary: str
    keyFactors: List[str]
    recommendations: List[str]

class ConfidenceFactors(BaseModel):
    dataCompleteness: float
    skillExtraction: float
    experienceAccuracy: float

class MatchMetadata(BaseModel):
    matchedAt: datetime
    processingTime: float
    algorithm: str
    confidenceFactors: ConfidenceFactors 

class MatchResponse(BaseModel):
    """
    This is the *full response body* for the POST /match endpoint.
    """
    matchId: uuid.UUID = Field(default_factory=uuid.uuid4)
    resumeId: uuid.UUID
    jobTitle: str
    company: str
    matchingResults: MatchingResults
    explanation: MatchExplanation
    metadata: MatchMetadata