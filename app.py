from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import random
import uuid
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from enum import Enum

# Initialize the Flask application
app = Flask(__name__)

# ===============================
# Data Models for Regulatory System
# ===============================

class WorkflowStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    APPROVED = "approved"
    REJECTED = "rejected"

class CheckStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"

class EntityType(Enum):
    HEDGE_FUND = "hedge_fund"
    INVESTMENT_ADVISOR = "investment_advisor"
    PENSION_FUND = "pension_fund"
    INSURANCE_COMPANY = "insurance_company"
    BANK = "bank"
    CORPORATE = "corporate"

@dataclass
class ProductApproval:
    product_name: str
    product_type: str
    approved_date: datetime
    risk_level: str

@dataclass
class ClientData:
    client_id: str
    entity_name: str
    entity_type: EntityType
    jurisdiction: str
    aum_usd: float
    business_type: str
    contact_person: str
    email: str
    approved_products: List[ProductApproval]
    created_at: datetime

@dataclass
class HighLevelCheck:
    check_id: str
    regulation_name: str
    check_description: str
    status: CheckStatus
    result_data: Dict
    created_at: datetime
    completed_at: Optional[datetime] = None

@dataclass
class DocumentCheck:
    check_id: str
    regulation_name: str
    document_type: str
    document_id: str
    ai_validation_status: CheckStatus
    manual_review_status: CheckStatus
    ai_confidence: float
    ai_feedback: str
    manual_notes: str
    created_at: datetime
    completed_at: Optional[datetime] = None

@dataclass
class DataQualityCheck:
    check_id: str
    regulation_name: str
    field_name: str
    status: CheckStatus
    dq_score: float
    issues: List[str]
    created_at: datetime
    completed_at: Optional[datetime] = None

@dataclass
class DocumentRequirement:
    document_type: str
    required: bool
    description: str

@dataclass
class RegulationRule:
    regulation_name: str
    conditions: Dict
    required_documents: List[DocumentRequirement]
    description: str

@dataclass
class WorkflowStep:
    step_name: str
    status: WorkflowStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    details: Dict
    error_message: Optional[str] = None

@dataclass
class ClientCommunication:
    comm_id: str
    client_id: str
    comm_type: str
    subject: str
    content: str
    status: WorkflowStatus
    sent_at: Optional[datetime]
    created_at: datetime

@dataclass
class RegulatoryWorkflow:
    workflow_id: str
    client_id: str
    client_data: Optional[ClientData]
    applicable_regulations: List[str]
    workflow_steps: Dict[str, WorkflowStep]  # step_name -> WorkflowStep
    classification_results: Optional['RegulatoryClassification']
    communications: List[ClientCommunication]
    overall_status: WorkflowStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

@dataclass
class RegulatoryClassification:
    client_id: str
    classification_id: str
    status: CheckStatus
    high_level_checks: List[HighLevelCheck]
    document_checks: List[DocumentCheck]
    dq_checks: List[DataQualityCheck]
    overall_progress: float
    created_at: datetime
    completed_at: Optional[datetime] = None

# ===============================
# Mock Data Storage
# ===============================

# In-memory storage for demo purposes
clients_db: Dict[str, ClientData] = {}
regulatory_db: Dict[str, RegulatoryClassification] = {}
workflow_db: Dict[str, RegulatoryWorkflow] = {}

# Regulation Classification Rules Engine
REGULATION_RULES = [
    RegulationRule(
        regulation_name="MiFID II",
        conditions={
            "jurisdiction": ["EU", "UK"],
            "products": ["derivatives", "equities", "bonds"],
            "entity_types": ["investment_advisor", "hedge_fund"],
            "aum_threshold": 5000000
        },
        required_documents=[
            DocumentRequirement("risk_disclosure", True, "Risk disclosure statement for MiFID II compliance"),
            DocumentRequirement("entity_registration", True, "Entity registration certificate"),
            DocumentRequirement("financial_statements", True, "Latest audited financial statements")
        ],
        description="Markets in Financial Instruments Directive II"
    ),
    RegulationRule(
        regulation_name="AIFMD",
        conditions={
            "jurisdiction": ["EU"],
            "products": ["alternative_investments", "hedge_funds"],
            "entity_types": ["hedge_fund", "investment_advisor"],
            "aum_threshold": 100000000
        },
        required_documents=[
            DocumentRequirement("aifmd_registration", True, "AIFMD registration documentation"),
            DocumentRequirement("fund_prospectus", True, "Fund prospectus and offering documents"),
            DocumentRequirement("risk_management", True, "Risk management framework documentation")
        ],
        description="Alternative Investment Fund Managers Directive"
    ),
    RegulationRule(
        regulation_name="EMIR",
        conditions={
            "jurisdiction": ["EU", "UK"],
            "products": ["derivatives", "swaps"],
            "entity_types": ["hedge_fund", "investment_advisor", "bank"],
            "aum_threshold": 0
        },
        required_documents=[
            DocumentRequirement("emir_registration", True, "EMIR registration and reporting documentation"),
            DocumentRequirement("derivative_policy", True, "Derivatives trading policy"),
            DocumentRequirement("risk_mitigation", True, "Risk mitigation procedures for OTC derivatives")
        ],
        description="European Market Infrastructure Regulation"
    ),
    RegulationRule(
        regulation_name="FATCA",
        conditions={
            "jurisdiction": ["US", "GLOBAL"],
            "entity_types": ["hedge_fund", "investment_advisor", "pension_fund", "insurance_company"],
            "aum_threshold": 0
        },
        required_documents=[
            DocumentRequirement("fatca_forms", True, "FATCA compliance forms (W-8 series)"),
            DocumentRequirement("us_person_identification", True, "US person identification procedures"),
            DocumentRequirement("irs_registration", False, "IRS registration documentation")
        ],
        description="Foreign Account Tax Compliance Act"
    ),
    RegulationRule(
        regulation_name="AML/KYC",
        conditions={
            "jurisdiction": ["GLOBAL"],
            "entity_types": ["hedge_fund", "investment_advisor", "bank", "corporate", "pension_fund", "insurance_company"],
            "aum_threshold": 0
        },
        required_documents=[
            DocumentRequirement("aml_policy", True, "Anti-Money Laundering policy and procedures"),
            DocumentRequirement("kyc_documentation", True, "Know Your Customer documentation"),
            DocumentRequirement("beneficial_ownership", True, "Beneficial ownership disclosure"),
            DocumentRequirement("sanctions_screening", True, "Sanctions screening procedures")
        ],
        description="Anti-Money Laundering / Know Your Customer"
    )
]

# Sample client data for demo (System X data)
SAMPLE_CLIENTS = {
    "CLIENT_001": {
        "entity_name": "European Alpha Fund",
        "entity_type": "hedge_fund",
        "jurisdiction": "EU",
        "aum_usd": 250000000,
        "business_type": "Alternative Investment Management",
        "contact_person": "Maria Schmidt",
        "email": "maria.schmidt@europealpha.com"
    },
    "CLIENT_002": {
        "entity_name": "Global Investment Advisors Ltd",
        "entity_type": "investment_advisor",
        "jurisdiction": "UK",
        "aum_usd": 75000000,
        "business_type": "Investment Advisory Services",
        "contact_person": "James Wilson",
        "email": "j.wilson@globalinvest.co.uk"
    },
    "CLIENT_003": {
        "entity_name": "US Pension Fund",
        "entity_type": "pension_fund",
        "jurisdiction": "US",
        "aum_usd": 500000000,
        "business_type": "Pension Fund Management",
        "contact_person": "Sarah Johnson",
        "email": "sarah.j@uspension.org"
    }
}

# Sample product approvals (System Y data)
SAMPLE_PRODUCTS = {
    "CLIENT_001": [
        {"product_name": "Equity Derivatives", "product_type": "derivatives", "risk_level": "high"},
        {"product_name": "European Equities", "product_type": "equities", "risk_level": "medium"},
        {"product_name": "Alternative Investments", "product_type": "alternative_investments", "risk_level": "high"}
    ],
    "CLIENT_002": [
        {"product_name": "Corporate Bonds", "product_type": "bonds", "risk_level": "low"},
        {"product_name": "Equity Trading", "product_type": "equities", "risk_level": "medium"}
    ],
    "CLIENT_003": [
        {"product_name": "Government Bonds", "product_type": "bonds", "risk_level": "low"},
        {"product_name": "Money Market", "product_type": "money_market", "risk_level": "low"}
    ]
}

# Mock data for client onboarding requests
def generate_mock_data():
    """Generate mock data for client onboarding dashboard"""

    # Define onboarding stages
    stages = [
        {'name': 'Regulatory Due Diligence', 'key': 'regulatory'},
        {'name': 'Contract Setup', 'key': 'contracts'},
        {'name': 'Account Setup', 'key': 'account_setup'},
        {'name': 'SSI Setup', 'key': 'ssi_setup'}
    ]


    # Generate stage-wise breakdown
    stage_data = {}
    total_in_progress = 0
    total_pending = 0
    total_completed = 0

    for stage in stages:
        stage_key = stage['key']
        in_progress = random.randint(8, 25)
        pending = random.randint(5, 15)
        completed = random.randint(15, 35)

        stage_data[stage_key] = {
            'name': stage['name'],
            'in_progress': in_progress,
            'pending': pending,
            'completed': completed,
            'total': in_progress + pending + completed
        }

        total_in_progress += in_progress
        total_pending += pending
        total_completed += completed

    # Calculate eligible to trade (completed all stages)
    eligible_to_trade = random.randint(18, 28)

    # Generate action items
    action_items = [
        {
            'title': 'Review missing ISDA',
            'client': 'Quantum Fund Ltd.',
            'priority': 'high',
            'due_date': datetime.now() + timedelta(days=2)
        },
        {
            'title': 'Approve SSI Setup',
            'client': 'Global Investments PLC',
            'priority': 'medium',
            'due_date': datetime.now() + timedelta(days=5)
        },
        {
            'title': 'Resolve DQ mismatch',
            'client': 'Pinnacle Corp.',
            'priority': 'low',
            'due_date': datetime.now() + timedelta(days=7)
        }
    ]

    return {
        'stage_data': stage_data,
        'totals': {
            'in_progress': total_in_progress,
            'pending': total_pending,
            'completed': total_completed,
            'eligible_to_trade': eligible_to_trade
        },
        'action_items': action_items
    }

# Define the main route for the dashboard
@app.route('/')
def dashboard():
    """
    Renders the main dashboard page with client onboarding data.
    """
    dashboard_data = generate_mock_data()
    return render_template('index.html', data=dashboard_data)

# API endpoint for dashboard data
@app.route('/api/dashboard')
def api_dashboard():
    """
    Returns dashboard data as JSON for API consumption.
    """
    return jsonify(generate_mock_data())

# Regulatory due diligence page
@app.route('/regulatory')
def regulatory_page():
    """
    Renders the regulatory due diligence page.
    """
    return render_template('regulatory.html')

# Contract setup page
@app.route('/contracts')
def contracts_page():
    """
    Renders the contract setup page.
    """
    return render_template('contracts.html')

# Account setup page
@app.route('/accounts')
def accounts_page():
    """
    Renders the account setup page.
    """
    return render_template('accounts.html')

# SSI setup page
@app.route('/ssi')
def ssi_page():
    """
    Renders the SSI setup page.
    """
    return render_template('ssi.html')

# ===============================
# New Regulatory Workflow Engine
# ===============================

def import_client_data(client_id: str) -> ClientData:
    """Simulate importing client data from System X and System Y"""
    if client_id not in SAMPLE_CLIENTS:
        raise ValueError(f"Client {client_id} not found in System X")

    client_info = SAMPLE_CLIENTS[client_id]
    products_info = SAMPLE_PRODUCTS.get(client_id, [])

    # Convert to ProductApproval objects
    approved_products = [
        ProductApproval(
            product_name=p["product_name"],
            product_type=p["product_type"],
            approved_date=datetime.now() - timedelta(days=random.randint(30, 365)),
            risk_level=p["risk_level"]
        ) for p in products_info
    ]

    return ClientData(
        client_id=client_id,
        entity_name=client_info["entity_name"],
        entity_type=EntityType(client_info["entity_type"]),
        jurisdiction=client_info["jurisdiction"],
        aum_usd=client_info["aum_usd"],
        business_type=client_info["business_type"],
        contact_person=client_info["contact_person"],
        email=client_info["email"],
        approved_products=approved_products,
        created_at=datetime.now()
    )

def classify_applicable_regulations(client_data: ClientData) -> List[str]:
    """Rule-based regulation classification based on client profile and products"""
    applicable_regulations = []

    client_product_types = [p.product_type for p in client_data.approved_products]

    for rule in REGULATION_RULES:
        is_applicable = True
        conditions = rule.conditions

        # Check jurisdiction
        if "jurisdiction" in conditions:
            if client_data.jurisdiction not in conditions["jurisdiction"] and "GLOBAL" not in conditions["jurisdiction"]:
                is_applicable = False

        # Check entity type
        if "entity_types" in conditions and is_applicable:
            if client_data.entity_type.value not in conditions["entity_types"]:
                is_applicable = False

        # Check AUM threshold
        if "aum_threshold" in conditions and is_applicable:
            if client_data.aum_usd < conditions["aum_threshold"]:
                is_applicable = False

        # Check product types
        if "products" in conditions and is_applicable:
            has_matching_product = any(product_type in client_product_types for product_type in conditions["products"])
            if not has_matching_product:
                is_applicable = False

        if is_applicable:
            applicable_regulations.append(rule.regulation_name)

    return applicable_regulations

def check_document_completeness(client_id: str, regulation_name: str) -> Dict:
    """Simulate checking document completeness from contract management system"""
    time.sleep(random.uniform(0.2, 0.8))  # Simulate API delay

    # Find the regulation rule
    rule = next((r for r in REGULATION_RULES if r.regulation_name == regulation_name), None)
    if not rule:
        return {"error": f"No rule found for {regulation_name}"}

    document_results = {}
    overall_complete = True

    for doc_req in rule.required_documents:
        # Simulate document availability (80% chance of being available)
        is_available = random.random() > 0.2

        if doc_req.required and not is_available:
            overall_complete = False

        document_results[doc_req.document_type] = {
            "required": doc_req.required,
            "available": is_available,
            "description": doc_req.description,
            "status": "complete" if is_available else ("missing" if doc_req.required else "optional_missing")
        }

    return {
        "regulation": regulation_name,
        "overall_complete": overall_complete,
        "documents": document_results,
        "checked_at": datetime.now().isoformat()
    }

def create_regulatory_workflow(client_id: str) -> RegulatoryWorkflow:
    """Create a new regulatory workflow for a client"""
    workflow_id = str(uuid.uuid4())

    # Initialize workflow steps
    workflow_steps = {
        "client_import": WorkflowStep(
            step_name="Client Data Import",
            status=WorkflowStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
            details={}
        ),
        "regulation_classification": WorkflowStep(
            step_name="Regulation Classification",
            status=WorkflowStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
            details={}
        ),
        "document_validation": WorkflowStep(
            step_name="Document Validation",
            status=WorkflowStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
            details={}
        ),
        "manual_review": WorkflowStep(
            step_name="Manual Review",
            status=WorkflowStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
            details={}
        ),
        "client_communication": WorkflowStep(
            step_name="Client Communication",
            status=WorkflowStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
            details={}
        )
    }

    workflow = RegulatoryWorkflow(
        workflow_id=workflow_id,
        client_id=client_id,
        client_data=None,
        applicable_regulations=[],
        workflow_steps=workflow_steps,
        classification_results=None,
        communications=[],
        overall_status=WorkflowStatus.NOT_STARTED,
        created_at=datetime.now()
    )

    workflow_db[workflow_id] = workflow
    return workflow

def process_workflow_step(workflow_id: str, step_name: str) -> bool:
    """Process a specific workflow step"""
    if workflow_id not in workflow_db:
        return False

    workflow = workflow_db[workflow_id]
    step = workflow.workflow_steps[step_name]

    step.started_at = datetime.now()
    step.status = WorkflowStatus.IN_PROGRESS

    try:
        if step_name == "client_import":
            # Import client data from systems X and Y
            workflow.client_data = import_client_data(workflow.client_id)
            step.details = {
                "system_x_data": "imported",
                "system_y_data": "imported",
                "products_count": len(workflow.client_data.approved_products)
            }

        elif step_name == "regulation_classification":
            # Classify applicable regulations
            workflow.applicable_regulations = classify_applicable_regulations(workflow.client_data)
            step.details = {
                "total_regulations_checked": len(REGULATION_RULES),
                "applicable_regulations": workflow.applicable_regulations,
                "classification_basis": "automated_rules_engine"
            }

        elif step_name == "document_validation":
            # Check document completeness for each regulation
            doc_results = {}
            overall_complete = True

            for regulation in workflow.applicable_regulations:
                result = check_document_completeness(workflow.client_id, regulation)
                doc_results[regulation] = result
                if not result.get("overall_complete", False):
                    overall_complete = False

            step.details = {
                "regulations_checked": len(workflow.applicable_regulations),
                "document_results": doc_results,
                "overall_complete": overall_complete
            }

            # If documents incomplete, require manual review
            if not overall_complete:
                step.status = WorkflowStatus.MANUAL_REVIEW_REQUIRED
                workflow.workflow_steps["manual_review"].status = WorkflowStatus.PENDING

        elif step_name == "manual_review":
            # Simulate manual review process
            time.sleep(random.uniform(1.0, 2.0))

            # 90% chance of approval
            approved = random.random() > 0.1
            step.details = {
                "reviewer": "Anna Vance",
                "review_decision": "approved" if approved else "rejected",
                "review_comments": "All regulatory requirements satisfied" if approved else "Missing critical documentation",
                "review_duration_minutes": random.randint(15, 45)
            }

            if approved:
                step.status = WorkflowStatus.APPROVED
            else:
                step.status = WorkflowStatus.REJECTED
                workflow.overall_status = WorkflowStatus.REJECTED
                return True

        elif step_name == "client_communication":
            # Generate and send client communication
            comm_id = str(uuid.uuid4())

            regulation_list = ", ".join(workflow.applicable_regulations)
            communication = ClientCommunication(
                comm_id=comm_id,
                client_id=workflow.client_id,
                comm_type="market_regulation_notification",
                subject=f"Regulatory Due Diligence Complete - {workflow.client_data.entity_name}",
                content=f"Dear {workflow.client_data.contact_person},\n\nWe have completed the regulatory due diligence for {workflow.client_data.entity_name}. Based on your entity profile and approved products, the following regulations are applicable: {regulation_list}.\n\nYour account is now eligible for trading activities.\n\nBest regards,\nRegulatory Team",
                status=WorkflowStatus.COMPLETED,
                sent_at=datetime.now(),
                created_at=datetime.now()
            )

            workflow.communications.append(communication)
            step.details = {
                "communication_type": "market_regulation_notification",
                "sent_to": workflow.client_data.email,
                "regulations_notified": workflow.applicable_regulations
            }

        # Complete the step
        if step.status not in [WorkflowStatus.MANUAL_REVIEW_REQUIRED, WorkflowStatus.REJECTED]:
            step.status = WorkflowStatus.COMPLETED
        step.completed_at = datetime.now()

        return True

    except Exception as e:
        step.status = WorkflowStatus.FAILED
        step.error_message = str(e)
        step.completed_at = datetime.now()
        return False

# ===============================
# Mock APIs for External Systems
# ===============================

def mock_document_api(client_id: str, regulation: str) -> Dict:
    """Simulate fetching document from upstream system"""
    time.sleep(random.uniform(0.1, 0.3))  # Simulate API delay

    return {
        'document_id': f"DOC_{client_id}_{regulation}_{random.randint(1000, 9999)}",
        'document_type': 'regulatory_compliance_statement',
        'content': f"Mock OCR extracted content for {regulation} compliance document. This document certifies that {client_id} meets the requirements for {regulation} regulation. Key compliance points: 1) Entity registration verified 2) Business activities approved 3) Financial thresholds met 4) Reporting obligations understood.",
        'metadata': {
            'file_size_kb': random.randint(50, 500),
            'pages': random.randint(1, 10),
            'created_date': datetime.now().isoformat(),
            'source_system': 'upstream_compliance_db'
        }
    }

def mock_llm_document_validation(content: str, regulation: str) -> Dict:
    """Simulate LLM analysis of document content"""
    time.sleep(random.uniform(0.2, 0.5))  # Simulate LLM processing

    # Simple mock logic based on content
    confidence = random.uniform(0.7, 0.95)
    is_compliant = confidence > 0.8

    validation_points = [
        f"Document type matches expected {regulation} compliance format",
        "Entity registration information present",
        "Business activity descriptions align with regulatory requirements",
        "Financial disclosure sections complete",
        "Signature and authorization sections validated"
    ]

    issues = [] if is_compliant else [
        f"Missing specific {regulation} compliance sections",
        "Incomplete entity information",
        "Unclear business activity descriptions"
    ]

    return {
        'is_compliant': is_compliant,
        'confidence_score': confidence,
        'validation_points': validation_points[:random.randint(3, 5)],
        'issues_found': issues,
        'recommendation': 'APPROVED' if is_compliant else 'MANUAL_REVIEW_REQUIRED',
        'analysis_summary': f"Document analysis for {regulation} shows {'strong compliance indicators' if is_compliant else 'areas requiring manual review'}."
    }

def mock_dq_api(client_id: str, regulation: str) -> Dict:
    """Simulate data quality checks from external system"""
    time.sleep(random.uniform(0.1, 0.4))  # Simulate API delay

    fields_to_check = [
        'entity_name', 'registration_number', 'jurisdiction',
        'business_address', 'contact_information', 'financial_data',
        'regulatory_permissions', 'reporting_obligations'
    ]

    dq_results = {}
    overall_score = 0
    total_fields = len(fields_to_check)

    for field in fields_to_check:
        score = random.uniform(0.6, 1.0)
        issues = []

        if score < 0.8:
            issues = [
                f"Data completeness: {field} missing required sub-fields",
                f"Data format: {field} format validation failed",
                f"Data freshness: {field} last updated > 90 days ago"
            ]

        dq_results[field] = {
            'score': score,
            'status': 'PASSED' if score >= 0.8 else 'FAILED',
            'issues': issues[:random.randint(0, 2)]
        }
        overall_score += score

    overall_score /= total_fields

    return {
        'client_id': client_id,
        'regulation': regulation,
        'overall_dq_score': overall_score,
        'overall_status': 'PASSED' if overall_score >= 0.8 else 'FAILED',
        'field_results': dq_results,
        'checked_at': datetime.now().isoformat(),
        'recommendations': [
            "Update stale data fields within 30 days",
            "Validate business address against official registries",
            "Complete missing regulatory permission documentation"
        ] if overall_score < 0.8 else []
    }

# ===============================
# Regulatory Processing Engine
# ===============================

def generate_high_level_checks(client_data: ClientData, regulations: List[str]) -> List[HighLevelCheck]:
    """Generate high-level regulatory checks based on client data"""
    checks = []

    for regulation in regulations:
        # Mock business logic for high-level checks
        check_passed = True
        result_data = {
            'aum_threshold_met': client_data.aum_usd >= 100_000_000 if regulation in ['AIFMD', 'UCITS'] else True,
            'jurisdiction_supported': client_data.jurisdiction in ['US', 'UK', 'EU', 'SG'],
            'entity_type_eligible': client_data.entity_type.value in ['hedge_fund', 'investment_advisor', 'bank'],
            'business_type_approved': 'investment' in client_data.business_type.lower()
        }

        # Determine overall status
        if not all(result_data.values()):
            check_passed = False

        check = HighLevelCheck(
            check_id=str(uuid.uuid4()),
            regulation_name=regulation,
            check_description=f"High-level eligibility check for {regulation}",
            status=CheckStatus.PASSED if check_passed else CheckStatus.FAILED,
            result_data=result_data,
            created_at=datetime.now(),
            completed_at=datetime.now()
        )
        checks.append(check)

    return checks

def process_document_checks(client_id: str, regulations: List[str]) -> List[DocumentCheck]:
    """Process document validation for all regulations"""
    checks = []

    for regulation in regulations:
        # Fetch document from upstream
        doc_data = mock_document_api(client_id, regulation)

        # Run LLM validation
        llm_result = mock_llm_document_validation(doc_data['content'], regulation)

        # Determine statuses
        ai_status = CheckStatus.PASSED if llm_result['is_compliant'] else CheckStatus.MANUAL_REVIEW
        manual_status = CheckStatus.PENDING if ai_status == CheckStatus.MANUAL_REVIEW else CheckStatus.PASSED

        check = DocumentCheck(
            check_id=str(uuid.uuid4()),
            regulation_name=regulation,
            document_type=doc_data['document_type'],
            document_id=doc_data['document_id'],
            ai_validation_status=ai_status,
            manual_review_status=manual_status,
            ai_confidence=llm_result['confidence_score'],
            ai_feedback=llm_result['analysis_summary'],
            manual_notes="",
            created_at=datetime.now(),
            completed_at=datetime.now() if ai_status == CheckStatus.PASSED else None
        )
        checks.append(check)

    return checks

def process_dq_checks(client_id: str, regulations: List[str]) -> List[DataQualityCheck]:
    """Process data quality checks for all regulations"""
    checks = []

    for regulation in regulations:
        dq_result = mock_dq_api(client_id, regulation)

        for field_name, field_result in dq_result['field_results'].items():
            check = DataQualityCheck(
                check_id=str(uuid.uuid4()),
                regulation_name=regulation,
                field_name=field_name,
                status=CheckStatus.PASSED if field_result['status'] == 'PASSED' else CheckStatus.FAILED,
                dq_score=field_result['score'],
                issues=field_result['issues'],
                created_at=datetime.now(),
                completed_at=datetime.now()
            )
            checks.append(check)

    return checks

def trigger_regulatory_classification(client_data: ClientData) -> RegulatoryClassification:
    """Main function to trigger regulatory classification process"""

    # Select random subset of regulations (simulate business rules)
    applicable_regulations = random.sample(REGULATIONS, random.randint(5, 10))

    print(f"Starting regulatory classification for {client_data.client_id}")
    print(f"Applicable regulations: {applicable_regulations}")

    # Process all three check categories in parallel (simulated)
    high_level_checks = generate_high_level_checks(client_data, applicable_regulations)
    document_checks = process_document_checks(client_data.client_id, applicable_regulations)
    dq_checks = process_dq_checks(client_data.client_id, applicable_regulations)

    # Calculate overall progress
    total_checks = len(high_level_checks) + len(document_checks) + len(dq_checks)
    completed_checks = sum([
        1 for check in high_level_checks if check.status in [CheckStatus.PASSED, CheckStatus.FAILED]
    ]) + sum([
        1 for check in document_checks if check.ai_validation_status in [CheckStatus.PASSED, CheckStatus.FAILED]
    ]) + sum([
        1 for check in dq_checks if check.status in [CheckStatus.PASSED, CheckStatus.FAILED]
    ])

    progress = (completed_checks / total_checks) * 100 if total_checks > 0 else 0

    # Determine overall status
    failed_checks = sum([
        1 for check in high_level_checks if check.status == CheckStatus.FAILED
    ]) + sum([
        1 for check in dq_checks if check.status == CheckStatus.FAILED
    ])

    manual_review_needed = sum([
        1 for check in document_checks if check.ai_validation_status == CheckStatus.MANUAL_REVIEW
    ])

    if failed_checks > 0:
        overall_status = CheckStatus.FAILED
    elif manual_review_needed > 0:
        overall_status = CheckStatus.MANUAL_REVIEW
    else:
        overall_status = CheckStatus.PASSED

    classification = RegulatoryClassification(
        client_id=client_data.client_id,
        classification_id=str(uuid.uuid4()),
        status=overall_status,
        high_level_checks=high_level_checks,
        document_checks=document_checks,
        dq_checks=dq_checks,
        overall_progress=progress,
        created_at=datetime.now(),
        completed_at=datetime.now() if overall_status in [CheckStatus.PASSED, CheckStatus.FAILED] else None
    )

    # Store in database
    regulatory_db[classification.classification_id] = classification

    print(f"Regulatory classification completed with status: {overall_status.value}")
    return classification

# ===============================
# API Endpoints for Regulatory System
# ===============================

@app.route('/api/regulatory/trigger', methods=['POST'])
def trigger_regulatory_process():
    """API endpoint to trigger regulatory classification from upstream system"""
    data = request.json

    # Validate required fields
    required_fields = ['client_id', 'entity_name', 'entity_type', 'jurisdiction', 'aum_usd', 'business_type']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        # Create client data object
        client_data = ClientData(
            client_id=data['client_id'],
            entity_name=data['entity_name'],
            entity_type=EntityType(data['entity_type']),
            jurisdiction=data['jurisdiction'],
            aum_usd=float(data['aum_usd']),
            business_type=data['business_type'],
            contact_person=data.get('contact_person', ''),
            email=data.get('email', ''),
            created_at=datetime.now()
        )

        # Store client data
        clients_db[client_data.client_id] = client_data

        # Trigger regulatory classification
        classification = trigger_regulatory_classification(client_data)

        return jsonify({
            'status': 'success',
            'classification_id': classification.classification_id,
            'overall_status': classification.status.value,
            'progress': classification.overall_progress,
            'message': f'Regulatory classification initiated for client {client_data.client_id}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/regulatory/status/<classification_id>')
def get_regulatory_status(classification_id):
    """Get detailed regulatory classification status"""
    if classification_id not in regulatory_db:
        return jsonify({'error': 'Classification not found'}), 404

    classification = regulatory_db[classification_id]

    # Convert to serializable format
    def convert_check_to_dict(check):
        result = asdict(check)
        # Convert datetime objects to strings
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, CheckStatus):
                result[key] = value.value
        return result

    return jsonify({
        'classification_id': classification.classification_id,
        'client_id': classification.client_id,
        'status': classification.status.value,
        'progress': classification.overall_progress,
        'created_at': classification.created_at.isoformat(),
        'completed_at': classification.completed_at.isoformat() if classification.completed_at else None,
        'high_level_checks': [convert_check_to_dict(check) for check in classification.high_level_checks],
        'document_checks': [convert_check_to_dict(check) for check in classification.document_checks],
        'dq_checks': [convert_check_to_dict(check) for check in classification.dq_checks],
    })

@app.route('/api/regulatory/list')
def list_regulatory_classifications():
    """List all regulatory classifications"""
    classifications = []
    for classification in regulatory_db.values():
        client = clients_db.get(classification.client_id)
        classifications.append({
            'classification_id': classification.classification_id,
            'client_id': classification.client_id,
            'client_name': client.entity_name if client else 'Unknown',
            'status': classification.status.value,
            'progress': classification.overall_progress,
            'created_at': classification.created_at.isoformat(),
            'completed_at': classification.completed_at.isoformat() if classification.completed_at else None,
            'total_checks': len(classification.high_level_checks) + len(classification.document_checks) + len(classification.dq_checks)
        })

    return jsonify(classifications)

# ===============================
# New Workflow API Endpoints
# ===============================

@app.route('/api/regulatory/search_client/<client_id>')
def search_client(client_id):
    """Search for client in System X and preview data"""
    try:
        if client_id not in SAMPLE_CLIENTS:
            return jsonify({'error': 'Client not found in System X'}), 404

        client_info = SAMPLE_CLIENTS[client_id]
        products_info = SAMPLE_PRODUCTS.get(client_id, [])

        return jsonify({
            'client_id': client_id,
            'system_x_data': client_info,
            'system_y_data': {
                'products': products_info,
                'product_count': len(products_info)
            },
            'found': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/regulatory/workflow/create', methods=['POST'])
def create_workflow():
    """Create a new regulatory workflow for a client"""
    data = request.json
    client_id = data.get('client_id')

    if not client_id:
        return jsonify({'error': 'client_id is required'}), 400

    try:
        workflow = create_regulatory_workflow(client_id)
        return jsonify({
            'status': 'success',
            'workflow_id': workflow.workflow_id,
            'client_id': workflow.client_id,
            'steps': list(workflow.workflow_steps.keys()),
            'message': f'Workflow created for client {client_id}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/regulatory/workflow/<workflow_id>/step/<step_name>', methods=['POST'])
def process_step(workflow_id, step_name):
    """Process a specific workflow step"""
    try:
        success = process_workflow_step(workflow_id, step_name)
        if success:
            workflow = workflow_db[workflow_id]
            step = workflow.workflow_steps[step_name]

            return jsonify({
                'status': 'success',
                'step_name': step_name,
                'step_status': step.status.value,
                'step_details': step.details,
                'started_at': step.started_at.isoformat() if step.started_at else None,
                'completed_at': step.completed_at.isoformat() if step.completed_at else None,
                'error_message': step.error_message
            })
        else:
            return jsonify({'error': 'Failed to process step'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/regulatory/workflow/<workflow_id>')
def get_workflow_status(workflow_id):
    """Get complete workflow status"""
    if workflow_id not in workflow_db:
        return jsonify({'error': 'Workflow not found'}), 404

    workflow = workflow_db[workflow_id]

    # Convert workflow to serializable format
    def convert_step_to_dict(step):
        return {
            'step_name': step.step_name,
            'status': step.status.value,
            'started_at': step.started_at.isoformat() if step.started_at else None,
            'completed_at': step.completed_at.isoformat() if step.completed_at else None,
            'details': step.details,
            'error_message': step.error_message
        }

    def convert_comm_to_dict(comm):
        return {
            'comm_id': comm.comm_id,
            'comm_type': comm.comm_type,
            'subject': comm.subject,
            'content': comm.content,
            'status': comm.status.value,
            'sent_at': comm.sent_at.isoformat() if comm.sent_at else None,
            'created_at': comm.created_at.isoformat()
        }

    client_data_dict = None
    if workflow.client_data:
        client_data_dict = {
            'client_id': workflow.client_data.client_id,
            'entity_name': workflow.client_data.entity_name,
            'entity_type': workflow.client_data.entity_type.value,
            'jurisdiction': workflow.client_data.jurisdiction,
            'aum_usd': workflow.client_data.aum_usd,
            'business_type': workflow.client_data.business_type,
            'contact_person': workflow.client_data.contact_person,
            'email': workflow.client_data.email,
            'approved_products': [
                {
                    'product_name': p.product_name,
                    'product_type': p.product_type,
                    'approved_date': p.approved_date.isoformat(),
                    'risk_level': p.risk_level
                } for p in workflow.client_data.approved_products
            ]
        }

    return jsonify({
        'workflow_id': workflow.workflow_id,
        'client_id': workflow.client_id,
        'client_data': client_data_dict,
        'applicable_regulations': workflow.applicable_regulations,
        'workflow_steps': {name: convert_step_to_dict(step) for name, step in workflow.workflow_steps.items()},
        'communications': [convert_comm_to_dict(comm) for comm in workflow.communications],
        'overall_status': workflow.overall_status.value,
        'created_at': workflow.created_at.isoformat(),
        'completed_at': workflow.completed_at.isoformat() if workflow.completed_at else None
    })

@app.route('/api/regulatory/workflows')
def list_workflows():
    """List all regulatory workflows"""
    workflows = []
    for workflow in workflow_db.values():
        # Calculate progress
        total_steps = len(workflow.workflow_steps)
        completed_steps = sum(1 for step in workflow.workflow_steps.values() if step.status in [WorkflowStatus.COMPLETED, WorkflowStatus.APPROVED])
        progress = (completed_steps / total_steps) if total_steps > 0 else 0

        workflows.append({
            'workflow_id': workflow.workflow_id,
            'client_id': workflow.client_id,
            'client_name': workflow.client_data.entity_name if workflow.client_data else 'Unknown',
            'overall_status': workflow.overall_status.value,
            'progress': progress,
            'applicable_regulations_count': len(workflow.applicable_regulations),
            'created_at': workflow.created_at.isoformat(),
            'completed_at': workflow.completed_at.isoformat() if workflow.completed_at else None
        })

    return jsonify(workflows)

# This allows you to run the app directly from the command line
if __name__ == '__main__':
    # Setting debug=True allows for automatic reloading when you save changes
    app.run(debug=True, port=5001)
