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
class ClientData:
    client_id: str
    entity_name: str
    entity_type: EntityType
    jurisdiction: str
    aum_usd: float
    business_type: str
    contact_person: str
    email: str
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

# Sample regulations for demo
REGULATIONS = [
    "MiFID II", "AIFMD", "UCITS", "CRD IV", "Solvency II",
    "FATCA", "CRS", "AML/KYC", "GDPR", "Basel III",
    "EMIR", "SFDR", "PRIIPs", "MAR", "BMR",
    "CASS", "CSDR", "Settlement Finality", "Market Abuse", "Prospectus"
]

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

# This allows you to run the app directly from the command line
if __name__ == '__main__':
    # Setting debug=True allows for automatic reloading when you save changes
    app.run(debug=True, port=5001)
