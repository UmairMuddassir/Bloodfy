"""
Chatbot services - Smart rule-based NLP + Dialogflow integration + FAQ matching.
Works WITHOUT any external API by using comprehensive keyword matching
and pattern detection for blood bank management queries.
"""

import re
import logging
from typing import Optional, Tuple, List
from django.conf import settings
from django.db.models import Q

from .models import FAQ, ChatSession, ChatMessage

logger = logging.getLogger('bloodfy')


class DialogflowService:
    """
    Google Dialogflow integration for NLP-based chatbot responses.
    Falls back gracefully if Dialogflow is not configured.
    """

    def __init__(self):
        self.project_id = getattr(settings, 'DIALOGFLOW_PROJECT_ID', '')
        self.client = None

        if self.project_id:
            try:
                from google.cloud import dialogflow_v2 as dialogflow
                self.client = dialogflow.SessionsClient()
                logger.info("Dialogflow client initialized for project: %s", self.project_id)
            except ImportError:
                logger.warning("google-cloud-dialogflow not installed. Using FAQ fallback.")
            except Exception as e:
                logger.warning("Dialogflow init failed: %s. Using FAQ fallback.", e)

    @property
    def is_configured(self):
        """Check if Dialogflow is properly configured."""
        return self.client is not None and bool(self.project_id)

    def detect_intent(self, text: str, session_id: str = 'default') -> Optional[dict]:
        """
        Send text to Dialogflow and get intent response.
        """
        if not self.is_configured:
            return None

        try:
            from google.cloud import dialogflow_v2 as dialogflow

            session_path = self.client.session_path(self.project_id, session_id)
            text_input = dialogflow.TextInput(text=text, language_code='en')
            query_input = dialogflow.QueryInput(text=text_input)

            response = self.client.detect_intent(
                session=session_path,
                query_input=query_input,
            )

            result = response.query_result

            return {
                'response': result.fulfillment_text,
                'intent': result.intent.display_name,
                'confidence': result.intent_detection_confidence,
            }

        except Exception as e:
            logger.error("Dialogflow detect_intent failed: %s", e)
            return None


class ChatbotService:
    """
    Smart chatbot service for Bloodify — Blood Bank Management System.
    Uses comprehensive pattern matching, FAQ lookup, and live database queries
    to answer donor/patient/admin questions intelligently.
    """

    # =========================================================================
    # Intent patterns — each tuple: (intent_name, [patterns], response_func)
    # =========================================================================

    BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']

    def __init__(self, user=None):
        self.user = user
        self.dialogflow = DialogflowService()

    def process_query(self, message: str, session_id: str = None) -> dict:
        """
        Process a chat query and return response.
        Priority: Dialogflow → FAQ match → Smart intent detection → Fallback
        """
        message_lower = message.lower().strip()

        # 1. Try Dialogflow first (if configured)
        if self.dialogflow.is_configured:
            df_result = self.dialogflow.detect_intent(
                text=message,
                session_id=session_id or 'default',
            )
            if df_result and df_result.get('confidence', 0) > 0.5:
                suggestions = self._get_suggestions(df_result.get('intent', ''))
                return {
                    'message': df_result['response'],
                    'intent': df_result['intent'],
                    'confidence': df_result['confidence'],
                    'faq_id': None,
                    'suggestions': suggestions,
                    'source': 'dialogflow',
                }

        # 2. Try FAQ match
        faq_match, faq_confidence = self._match_faq(message_lower)
        if faq_match and faq_confidence > 0.4:
            faq_match.view_count += 1
            faq_match.save(update_fields=['view_count'])
            return {
                'message': faq_match.answer,
                'intent': 'faq_match',
                'confidence': faq_confidence,
                'faq_id': str(faq_match.id),
                'suggestions': self._get_suggestions('faq_match'),
                'source': 'faq',
            }

        # 3. Smart intent detection (rule-based NLP)
        response, intent, confidence = self._detect_intent(message_lower, message)
        return {
            'message': response,
            'intent': intent,
            'confidence': confidence,
            'faq_id': None,
            'suggestions': self._get_suggestions(intent),
            'source': 'local_nlu',
        }

    # =========================================================================
    # Smart Intent Detection — Comprehensive pattern matching
    # =========================================================================

    def _detect_intent(self, msg: str, original: str) -> Tuple[str, str, float]:
        """Detect intent from message using pattern matching."""

        # --- Greetings ---
        if self._matches(msg, ['hello', 'hi', 'hey', 'salam', 'assalam', 'good morning',
                                'good afternoon', 'good evening', 'howdy', 'hola']):
            user_name = self.user.first_name if self.user else 'there'
            return (
                f"Hello {user_name}! 👋 Welcome to Bloodify AI Assistant.\n\n"
                f"I can help you with:\n"
                f"🩸 Blood stock & availability\n"
                f"👤 Donor registration & eligibility\n"
                f"🔍 Finding compatible donors\n"
                f"🚨 Emergency blood requests\n"
                f"📊 System statistics & reports\n\n"
                f"What would you like to know?",
                'greeting', 0.95
            )

        # --- Blood Availability / Stock ---
        if self._matches(msg, ['stock', 'availability', 'available', 'units', 'how much blood',
                                'blood level', 'inventory', 'supply', 'blood bank']):
            blood_group = self._extract_blood_group(original)
            if blood_group:
                return self._get_blood_stock_response(blood_group), 'blood_availability', 0.9
            return self._get_all_stock_response(), 'blood_stock_overview', 0.85

        # --- Find / Search Donors ---
        if self._matches(msg, ['find donor', 'search donor', 'donor list', 'available donor',
                                'who can donate', 'compatible donor', 'match donor',
                                'nearby donor', 'locate donor']):
            blood_group = self._extract_blood_group(original)
            return self._get_find_donor_response(blood_group), 'find_donors', 0.9

        # --- Donor Registration ---
        if self._matches(msg, ['register', 'sign up', 'signup', 'become donor', 'join',
                                'create account', 'new donor', 'how to donate',
                                'want to donate', 'i want to donate']):
            return (
                "🩸 **How to Register as a Blood Donor:**\n\n"
                "**Step 1:** Create an account on Bloodify\n"
                "**Step 2:** Navigate to 'Donor Registration' page\n"
                "**Step 3:** Fill in your details:\n"
                "   • Full Name & Contact Number\n"
                "   • Blood Group (A+, B+, O-, etc.)\n"
                "   • City & Address\n"
                "   • Date of Birth\n"
                "**Step 4:** Submit — Admin will review & approve\n\n"
                "⏱ Approval usually takes 24-48 hours.\n"
                "📱 You'll receive a notification once approved!",
                'donor_registration', 0.9
            )

        # --- Eligibility ---
        if self._matches(msg, ['eligible', 'eligibility', 'can i donate', 'qualify',
                                'criteria', 'requirement', 'who can donate', 'conditions',
                                'am i eligible']):
            return (
                "✅ **Blood Donation Eligibility Criteria:**\n\n"
                "• **Age:** 18 - 65 years old\n"
                "• **Weight:** Minimum 50 kg (110 lbs)\n"
                "• **Health:** Generally in good health\n"
                "• **Gap:** At least 90 days since last donation\n"
                "• **No:** Active infections or blood-borne diseases\n"
                "• **No:** Recent surgery (within 6 months)\n"
                "• **No:** Pregnancy or breastfeeding\n\n"
                "⚠️ **Temporary Deferrals:**\n"
                "• Recent tattoo/piercing: Wait 6 months\n"
                "• Cold/flu: Wait until fully recovered\n"
                "• Medication: Consult with blood bank staff\n\n"
                "💡 When in doubt, our medical team will assess you during registration!",
                'eligibility_info', 0.9
            )

        # --- Emergency ---
        if self._matches(msg, ['emergency', 'urgent', 'critical', 'life saving',
                                'immediately', 'asap', 'rush', 'sos', 'life threatening']):
            return (
                "🚨 **Emergency Blood Request:**\n\n"
                "For emergencies, use the **Emergency** page in the sidebar!\n\n"
                "**Quick Steps:**\n"
                "1. Go to ⚡ **Emergency** page\n"
                "2. Select the required **Blood Group**\n"
                "3. Enter your **City/Hospital**\n"
                "4. Click **Search Donors**\n"
                "5. System will find the **nearest available donors**\n"
                "6. Click 📱 **SMS** or 📞 **Call** to contact them instantly\n\n"
                "⏱ Average response time: **Under 15 minutes**\n"
                "🤖 AI ranks donors by proximity, availability & compatibility!",
                'emergency_info', 0.95
            )

        # --- Blood Request (Patient) ---
        if self._matches(msg, ['request blood', 'need blood', 'blood request', 'patient',
                                'hospital need', 'transfusion', 'i need blood', 'require blood']):
            return (
                "🏥 **How to Create a Blood Request:**\n\n"
                "1. Go to **Blood Requests** page\n"
                "2. Click **'New Request'**\n"
                "3. Enter patient details:\n"
                "   • Patient name & hospital\n"
                "   • Required blood group & units\n"
                "   • Urgency level (Normal / Urgent / Critical)\n"
                "4. Submit the request\n\n"
                "🤖 **AI Auto-Matching:** Our system will automatically:\n"
                "   • Find compatible donors nearby\n"
                "   • Rank them by availability & distance\n"
                "   • Send SMS alerts to top matches\n\n"
                "📊 Track your request status in real-time!",
                'blood_request_info', 0.9
            )

        # --- Donation Process ---
        if self._matches(msg, ['donation process', 'how long', 'what happens', 'procedure',
                                'steps', 'process of donation', 'how donation works',
                                'during donation']):
            return (
                "💉 **Blood Donation Process:**\n\n"
                "1. **Registration** (5 min) — ID check & form filling\n"
                "2. **Screening** (10 min) — BP, hemoglobin & health check\n"
                "3. **Donation** (8-12 min) — Actual blood collection (~450ml)\n"
                "4. **Rest** (15 min) — Refreshments & monitoring\n\n"
                "⏱ **Total time:** About 30-45 minutes\n\n"
                "📋 **What to bring:**\n"
                "• Valid ID (CNIC/Passport)\n"
                "• Eat a healthy meal 2-3 hours before\n"
                "• Drink plenty of water\n"
                "• Get good sleep the night before\n\n"
                "🎁 **After donation:** Avoid heavy lifting for 24 hours!",
                'donation_process', 0.9
            )

        # --- Blood Group Info ---
        if self._matches(msg, ['blood type', 'blood group', 'what is my blood',
                                'compatible', 'compatibility', 'which blood can',
                                'universal donor', 'universal recipient']):
            return (
                "🩸 **Blood Group Compatibility Chart:**\n\n"
                "| Blood Type | Can Donate To | Can Receive From |\n"
                "| O- | Everyone (Universal Donor) | O- only |\n"
                "| O+ | O+, A+, B+, AB+ | O-, O+ |\n"
                "| A- | A-, A+, AB-, AB+ | O-, A- |\n"
                "| A+ | A+, AB+ | O-, O+, A-, A+ |\n"
                "| B- | B-, B+, AB-, AB+ | O-, B- |\n"
                "| B+ | B+, AB+ | O-, O+, B-, B+ |\n"
                "| AB- | AB-, AB+ | O-, A-, B-, AB- |\n"
                "| AB+ | AB+ only | Everyone (Universal Recipient) |\n\n"
                "💡 **O-** is the universal donor, **AB+** is the universal recipient!",
                'blood_compatibility', 0.9
            )

        # --- Statistics / Dashboard ---
        if self._matches(msg, ['statistics', 'stats', 'how many donor', 'total donor',
                                'dashboard', 'report', 'analytics', 'data', 'numbers']):
            return self._get_statistics_response(), 'statistics', 0.85

        # --- Contact / Support ---
        if self._matches(msg, ['contact', 'support', 'help', 'phone', 'email',
                                'customer service', 'complaint', 'feedback']):
            return (
                "📞 **Bloodify Support:**\n\n"
                "• **Emergency:** Use the Emergency page for immediate help\n"
                "• **Admin Support:** Contact your hospital's blood bank admin\n"
                "• **Technical Issues:** Check the Settings page\n"
                "• **Feedback:** We value your input!\n\n"
                "💡 You can also ask me any question about:\n"
                "• Blood donation eligibility\n"
                "• Finding donors\n"
                "• Blood stock levels\n"
                "• Registration process",
                'contact_support', 0.8
            )

        # --- Thank You ---
        if self._matches(msg, ['thank', 'thanks', 'thx', 'appreciate', 'great',
                                'awesome', 'perfect', 'wonderful', 'shukriya']):
            return (
                "You're welcome! 😊 Happy to help!\n\n"
                "Remember — every blood donation can save up to **3 lives**! 🩸\n\n"
                "Is there anything else you'd like to know?",
                'thanks', 0.9
            )

        # --- Goodbye ---
        if self._matches(msg, ['bye', 'goodbye', 'see you', 'exit', 'quit',
                                'close', 'khuda hafiz', 'allah hafiz']):
            return (
                "Goodbye! 👋 Thank you for using Bloodify.\n"
                "Stay healthy, and remember — donating blood saves lives! 🩸❤️",
                'goodbye', 0.9
            )

        # --- What can you do / About ---
        if self._matches(msg, ['what can you do', 'what do you do', 'capabilities',
                                'features', 'about', 'who are you', 'what is bloodify',
                                'tell me about']):
            return (
                "🤖 **I'm Bloodify AI Assistant!**\n\n"
                "I'm an intelligent chatbot built into the Bloodify Blood Bank Management System. "
                "Here's what I can do:\n\n"
                "🩸 **Blood Stock** — Check real-time blood availability\n"
                "👤 **Donors** — Find, register, or check eligibility\n"
                "🏥 **Requests** — Guide you through blood requests\n"
                "🚨 **Emergency** — Help with urgent blood needs\n"
                "📊 **Stats** — Show system statistics & analytics\n"
                "🧬 **Compatibility** — Blood group matching info\n"
                "📋 **Process** — Explain donation procedures\n\n"
                "💡 Just type your question and I'll help!",
                'about_bot', 0.9
            )

        # --- Benefits of Donating ---
        if self._matches(msg, ['benefit', 'advantage', 'why donate', 'why should i', 'importance', 'save lives']):
            return (
                "❤️ **Benefits of Blood Donation:**\n\n"
                "🩺 **Health Benefits:**\n"
                "• Free health screening (BP, hemoglobin, diseases)\n"
                "• Reduces iron overload — lowers heart disease risk\n"
                "• Stimulates new blood cell production\n"
                "• Burns ~650 calories per donation\n\n"
                "🌍 **Social Impact:**\n"
                "• One donation saves up to **3 lives**\n"
                "• Helps accident victims, surgery patients, cancer patients\n"
                "• Blood cannot be manufactured — only donated\n"
                "• Every 2 seconds someone needs blood",
                'benefits', 0.9
            )

        # --- Side Effects / Risks ---
        if self._matches(msg, ['side effect', 'risk', 'danger', 'harmful', 'safe to donate', 'pain', 'hurt', 'faint', 'dizzy']):
            return (
                "⚠️ **Side Effects of Blood Donation:**\n\n"
                "**Common (mild & temporary):**\n"
                "• Slight bruising at needle site\n"
                "• Mild dizziness (1-2 minutes)\n"
                "• Light-headedness if you skip meals\n\n"
                "**Rare:**\n"
                "• Fainting (less than 1% of donors)\n"
                "• Nausea — usually from anxiety\n\n"
                "✅ **Blood donation is VERY SAFE** when done at certified centers.\n"
                "💡 Eat well & drink water before donating to minimize effects.",
                'side_effects', 0.9
            )

        # --- After Donation Care ---
        if self._matches(msg, ['after donat', 'post donat', 'recovery', 'care after', 'what to do after', 'rest after']):
            return (
                "🩹 **After Donation Care:**\n\n"
                "**Immediately (15 min):**\n"
                "• Rest in the recovery area\n"
                "• Drink juice/water provided\n"
                "• Eat a light snack\n\n"
                "**Next 24 Hours:**\n"
                "• Drink extra fluids (8+ glasses)\n"
                "• Avoid heavy lifting or exercise\n"
                "• Keep bandage on for 4-5 hours\n"
                "• Avoid alcohol for 24 hours\n\n"
                "**Next 2-3 Days:**\n"
                "• Eat iron-rich foods (spinach, red meat, beans)\n"
                "• Your body replaces blood volume in 24-48 hours\n"
                "• Red blood cells fully replenish in 4-8 weeks",
                'after_care', 0.9
            )

        # --- Blood Storage / Shelf Life ---
        if self._matches(msg, ['storage', 'shelf life', 'how long blood last', 'expire', 'preserve', 'store blood']):
            return (
                "🧊 **Blood Storage & Shelf Life:**\n\n"
                "• **Whole Blood:** 35-42 days (refrigerated 1-6°C)\n"
                "• **Red Blood Cells:** 42 days (refrigerated)\n"
                "• **Platelets:** Only 5 days (room temp with agitation)\n"
                "• **Plasma:** Up to 1 year (frozen at -18°C)\n\n"
                "⚠️ This is why **regular donors** are critical!\n"
                "Platelets expire in just 5 days — constant supply needed.",
                'blood_storage', 0.9
            )

        # --- Blood Components ---
        if self._matches(msg, ['component', 'rbc', 'plasma', 'platelet', 'white blood', 'red blood cell', 'what is blood made']):
            return (
                "🧬 **Blood Components:**\n\n"
                "🔴 **Red Blood Cells (RBC):** Carry oxygen to body tissues\n"
                "⚪ **White Blood Cells (WBC):** Fight infections\n"
                "🟡 **Platelets:** Help blood clot & stop bleeding\n"
                "💛 **Plasma:** Liquid that carries cells, proteins & nutrients\n\n"
                "💡 One unit of donated blood is separated into these components,\n"
                "each helping different patients — that's how **1 donation = 3 lives saved!**",
                'blood_components', 0.9
            )

        # --- Rare Blood Types ---
        if self._matches(msg, ['rare blood', 'rarest', 'uncommon blood', 'bombay blood', 'golden blood']):
            return (
                "💎 **Rare Blood Types:**\n\n"
                "• **AB-** — Rarest common type (~1% population)\n"
                "• **B-** — Very rare (~2% population)\n"
                "• **Bombay Blood (Oh)** — Extremely rare, found in India/Pakistan\n"
                "• **Rh-null (Golden Blood)** — Rarest in the world (<50 people known)\n\n"
                "🩸 **O-** is the universal donor (gives to everyone)\n"
                "🩸 **AB+** is the universal recipient (receives from everyone)\n\n"
                "If you have a rare blood type, your donation is EXTREMELY valuable!",
                'rare_blood', 0.9
            )

        # --- Donation Frequency ---
        if self._matches(msg, ['how often', 'frequency', 'how many times', 'gap between', 'wait between', 'interval', 'next donation']):
            return (
                "⏱ **Donation Frequency:**\n\n"
                "• **Whole Blood:** Every **90 days** (3 months)\n"
                "• **Platelets:** Every **7 days** (up to 24 times/year)\n"
                "• **Plasma:** Every **28 days**\n"
                "• **Double Red Cells:** Every **112 days**\n\n"
                "📋 Bloodify automatically tracks your last donation date\n"
                "and notifies you when you're eligible again!",
                'donation_frequency', 0.9
            )

        # --- Medical Conditions ---
        if self._matches(msg, ['diabetes', 'heart disease', 'cancer', 'hiv', 'hepatitis', 'malaria',
                                'disease', 'medical condition', 'health issue', 'chronic', 'anemia']):
            return (
                "🏥 **Medical Conditions & Donation:**\n\n"
                "**Cannot Donate:**\n"
                "• HIV/AIDS positive\n"
                "• Hepatitis B or C\n"
                "• Active cancer treatment\n"
                "• Severe heart disease\n\n"
                "**Can Donate (with conditions):**\n"
                "• Diabetes (if controlled with medication)\n"
                "• High BP (if controlled, BP < 180/100)\n"
                "• Thyroid conditions (if stable)\n"
                "• Past malaria (wait 3 years after treatment)\n\n"
                "⚠️ Always inform the blood bank about your medical history!",
                'medical_conditions', 0.9
            )

        # --- Medications ---
        if self._matches(msg, ['medication', 'medicine', 'drug', 'antibiotic', 'aspirin', 'taking pills']):
            return (
                "💊 **Medications & Blood Donation:**\n\n"
                "**Wait Period Required:**\n"
                "• Antibiotics: Wait 24-72 hours after finishing course\n"
                "• Aspirin: Wait 48 hours before platelet donation\n"
                "• Blood thinners: Cannot donate while on them\n"
                "• Accutane: Wait 1 month after stopping\n\n"
                "**OK to Donate:**\n"
                "• Vitamins & supplements\n"
                "• Birth control pills\n"
                "• Thyroid medication\n"
                "• Blood pressure medication (if BP is controlled)\n\n"
                "💡 Always tell the screening staff about your medications!",
                'medications', 0.9
            )

        # --- Tattoo / Piercing ---
        if self._matches(msg, ['tattoo', 'piercing', 'ink', 'body art', 'ear piercing']):
            return (
                "🎨 **Tattoos/Piercings & Donation:**\n\n"
                "• **Wait 6 months** after getting a tattoo\n"
                "• **Wait 6 months** after body piercing\n"
                "• Ear piercing with sterile equipment: **Wait 1 month**\n\n"
                "This waiting period ensures no infections were transmitted.\n"
                "After the wait, you can donate normally! ✅",
                'tattoo_piercing', 0.9
            )

        # --- Pregnancy ---
        if self._matches(msg, ['pregnant', 'pregnancy', 'breastfeed', 'nursing', 'expecting', 'baby']):
            return (
                "🤰 **Pregnancy & Blood Donation:**\n\n"
                "• **During pregnancy:** Cannot donate ❌\n"
                "• **After delivery:** Wait **6 months** before donating\n"
                "• **While breastfeeding:** Wait until weaning\n"
                "• **After miscarriage:** Wait 6 months\n\n"
                "This protects both mother and baby's health.\n"
                "After the waiting period, you're welcome to donate! 💪",
                'pregnancy', 0.9
            )

        # --- Hemoglobin / Iron ---
        if self._matches(msg, ['hemoglobin', 'iron', 'hb level', 'haemoglobin', 'iron deficien']):
            return (
                "🔬 **Hemoglobin & Iron Levels:**\n\n"
                "**Minimum Hemoglobin to Donate:**\n"
                "• Men: **13.0 g/dL**\n"
                "• Women: **12.5 g/dL**\n\n"
                "**Boost Your Iron Levels:**\n"
                "• Red meat, liver & fish\n"
                "• Spinach, lentils & beans\n"
                "• Fortified cereals\n"
                "• Vitamin C helps iron absorption\n\n"
                "💡 Your hemoglobin is checked FREE before every donation!",
                'hemoglobin', 0.9
            )

        # --- Appointment / Location ---
        if self._matches(msg, ['appointment', 'book', 'schedule', 'location', 'nearest', 'where to donate',
                                'blood bank near', 'address', 'timings', 'hours', 'open']):
            return (
                "📍 **Finding a Blood Bank / Booking:**\n\n"
                "**In Bloodify:**\n"
                "• Use the **Emergency** page to find nearest donors/banks\n"
                "• AI shows donors ranked by distance from you\n"
                "• Direct **Call** or **SMS** contact available\n\n"
                "**General Tips:**\n"
                "• Most blood banks operate 9 AM - 5 PM\n"
                "• Hospitals accept donations 24/7 for emergencies\n"
                "• No appointment needed for walk-in donations\n\n"
                "💡 Use our Emergency Search to find help nearby!",
                'appointment', 0.85
            )

        # --- Blood Drive / Camp ---
        if self._matches(msg, ['blood drive', 'blood camp', 'donation camp', 'organize', 'arrange', 'event']):
            return (
                "🏕 **Blood Donation Drives/Camps:**\n\n"
                "**How to Organize:**\n"
                "1. Partner with a registered blood bank\n"
                "2. Choose a venue (school, office, mosque, community center)\n"
                "3. Promote through social media & Bloodify\n"
                "4. Target at least 25-50 donors per drive\n"
                "5. Ensure medical staff & equipment are present\n\n"
                "📊 Bloodify can help manage donor registrations\n"
                "and send bulk SMS notifications for drives!",
                'blood_drive', 0.85
            )

        # --- COVID & Donation ---
        if self._matches(msg, ['covid', 'corona', 'vaccine', 'vaccinated', 'covid-19', 'pandemic']):
            return (
                "🦠 **COVID-19 & Blood Donation:**\n\n"
                "• **After COVID infection:** Wait **14 days** after full recovery\n"
                "• **After COVID vaccine:** Can donate **immediately** (no wait)\n"
                "• COVID does NOT spread through blood transfusion\n"
                "• All donated blood is tested for infectious diseases\n\n"
                "✅ Blood donation is **safe** during and after the pandemic.\n"
                "🩸 Blood supply is critically needed — please donate!",
                'covid', 0.9
            )

        # --- Transfusion Info ---
        if self._matches(msg, ['transfusion', 'receive blood', 'getting blood', 'blood given to patient']):
            return (
                "💉 **Blood Transfusion:**\n\n"
                "**Who Needs Transfusions:**\n"
                "• Surgery patients\n"
                "• Accident/trauma victims\n"
                "• Cancer patients during chemotherapy\n"
                "• Thalassemia & sickle cell patients\n"
                "• Women with complications during childbirth\n\n"
                "**Process:**\n"
                "• Blood is cross-matched to ensure compatibility\n"
                "• Takes 1-4 hours depending on volume\n"
                "• Monitored by medical staff throughout\n\n"
                "🩸 Every unit of blood donated is thoroughly tested before use.",
                'transfusion', 0.9
            )

        # --- Profile / Account ---
        if self._matches(msg, ['profile', 'account', 'update', 'change password', 'edit', 'my info', 'settings']):
            return (
                "👤 **Profile & Account Management:**\n\n"
                "• Go to **Settings** page to update your profile\n"
                "• Change your phone number, address, or city\n"
                "• Update your blood group if incorrectly set\n"
                "• Use **Forgot Password** on login page to reset password\n\n"
                "📱 Keep your phone number updated — it's used for\n"
                "emergency SMS alerts and donor notifications!",
                'profile', 0.85
            )

        # --- Admin Functions ---
        if self._matches(msg, ['admin', 'approve donor', 'manage', 'pending request', 'assign donor', 'admin panel']):
            return (
                "🔧 **Admin Functions:**\n\n"
                "**Dashboard:** Overview of donors, requests & stock\n"
                "**Donors:** Approve/reject new donor registrations\n"
                "**Blood Requests:** Manage incoming blood requests\n"
                "**Blood Stock:** Update inventory levels per blood group\n"
                "**Emergency:** Search & contact donors for urgent needs\n"
                "**Analytics:** AI-powered insights & predictions\n\n"
                "💡 Use the sidebar to navigate between admin pages!",
                'admin_functions', 0.85
            )

        # --- Thalassemia ---
        if self._matches(msg, ['thalassemia', 'sickle cell', 'hemophilia', 'blood disorder', 'blood disease']):
            return (
                "🩺 **Blood Disorders:**\n\n"
                "**Thalassemia:**\n"
                "• Genetic disorder — patients need regular transfusions\n"
                "• Major patients need blood every 2-4 weeks\n"
                "• Bloodify helps find compatible donors quickly\n\n"
                "**Sickle Cell Disease:**\n"
                "• Abnormal hemoglobin causes cell shape changes\n"
                "• May need transfusions during crisis episodes\n\n"
                "🩸 Regular blood donors are lifelines for these patients!\n"
                "Please donate regularly — your blood saves chronic patients!",
                'blood_disorders', 0.9
            )

        # --- What is Bloodify / System ---
        if self._matches(msg, ['how does system', 'how bloodify work', 'ai system', 'technology', 'how does ai',
                                'algorithm', 'machine learning', 'artificial intelligence']):
            return (
                "🤖 **How Bloodify Works:**\n\n"
                "**AI-Powered Blood Bank Management System**\n\n"
                "1️⃣ **Smart Donor Matching** — AI ranks donors by:\n"
                "   • Blood group compatibility\n"
                "   • Geographic proximity (Haversine formula)\n"
                "   • Availability & response history\n"
                "   • Medical eligibility score\n\n"
                "2️⃣ **Emergency System** — Finds nearest donors instantly\n"
                "3️⃣ **Twilio SMS** — Auto-notifies donors via SMS\n"
                "4️⃣ **Real-time Stock** — Tracks blood inventory across hospitals\n"
                "5️⃣ **AI Triage** — Prioritizes urgent requests automatically\n\n"
                "Built with: Django REST + Vanilla JS + Leaflet Maps + Twilio",
                'system_info', 0.9
            )

        # --- Default / Fallback ---
        return (
            "I understand you're asking about something. Let me help! 🤔\n\n"
            "Here are some things you can ask me:\n\n"
            "🩸 **\"Check A+ stock\"** — Blood availability\n"
            "👤 **\"How to register as donor?\"** — Registration guide\n"
            "✅ **\"Am I eligible to donate?\"** — Eligibility criteria\n"
            "🚨 **\"Emergency blood request\"** — Emergency process\n"
            "🔍 **\"Find O- donors\"** — Search donors\n"
            "📊 **\"Show statistics\"** — System stats\n"
            "🧬 **\"Blood compatibility\"** — Compatibility chart\n"
            "💉 **\"Donation process\"** — Step by step guide\n"
            "❤️ **\"Benefits of donating\"** — Why donate?\n"
            "🦠 **\"COVID and donation\"** — COVID guidelines\n\n"
            "Try asking one of these! 😊",
            'fallback', 0.4
        )

    # =========================================================================
    # Helper — Pattern Matching
    # =========================================================================

    def _matches(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        return any(p in text for p in patterns)

    def _extract_blood_group(self, text: str) -> Optional[str]:
        """Extract blood group from text."""
        text_upper = text.upper().replace(' ', '')
        for bg in ['AB+', 'AB-', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-']:
            if bg in text_upper:
                return bg
        # Try word patterns: "a positive", "o negative"
        patterns = {
            'A POSITIVE': 'A+', 'A NEGATIVE': 'A-',
            'B POSITIVE': 'B+', 'B NEGATIVE': 'B-',
            'O POSITIVE': 'O+', 'O NEGATIVE': 'O-',
            'AB POSITIVE': 'AB+', 'AB NEGATIVE': 'AB-',
        }
        upper = text.upper()
        for pattern, bg in patterns.items():
            if pattern in upper:
                return bg
        return None

    # =========================================================================
    # Dynamic Responses — Query Database
    # =========================================================================

    def _get_blood_stock_response(self, blood_group: str) -> str:
        """Get blood stock for a specific blood group."""
        try:
            from blood_stock.models import BloodStock
            stocks = BloodStock.objects.filter(blood_group=blood_group)

            if not stocks.exists():
                return (
                    f"📊 No stock data found for **{blood_group}** in the system.\n\n"
                    f"This could mean:\n"
                    f"• No hospitals have reported {blood_group} stock yet\n"
                    f"• Stock data needs to be updated by admin\n\n"
                    f"💡 Contact your nearest blood bank for real-time availability."
                )

            response = f"🩸 **{blood_group} Blood Stock:**\n\n"
            total_units = 0
            for stock in stocks[:8]:
                status_emoji = "🟢" if not stock.is_low else ("🔴" if stock.is_critical else "🟡")
                response += f"{status_emoji} **{stock.hospital_name}** ({stock.hospital_city}): **{stock.units_available}** units\n"
                total_units += stock.units_available

            response += f"\n📦 **Total available:** {total_units} units across {stocks.count()} location(s)"

            if any(s.is_critical for s in stocks):
                response += "\n\n⚠️ Some locations are critically low! Consider donating."

            return response
        except Exception as e:
            logger.error("Blood stock query failed: %s", e)
            return f"Unable to fetch stock data for {blood_group} right now. Please check the Blood Stock page."

    def _get_all_stock_response(self) -> str:
        """Get overview of all blood stock."""
        try:
            from blood_stock.models import BloodStock
            stocks = BloodStock.objects.all()

            if not stocks.exists():
                return (
                    "📊 **Blood Stock Overview:**\n\n"
                    "No stock data available in the system yet.\n"
                    "Admin needs to add blood stock entries first.\n\n"
                    "💡 Ask about a specific blood group like: *\"Check A+ stock\"*"
                )

            # Group by blood group
            from django.db.models import Sum
            summary = stocks.values('blood_group').annotate(
                total=Sum('units_available')
            ).order_by('blood_group')

            response = "📊 **Blood Stock Overview:**\n\n"
            for item in summary:
                bg = item['blood_group']
                total = item['total']
                status_emoji = "🟢" if total >= 10 else ("🔴" if total < 3 else "🟡")
                response += f"{status_emoji} **{bg}:** {total} units\n"

            response += "\n💡 Ask *\"Check O+ stock\"* for detailed info on any blood group."
            return response
        except Exception as e:
            logger.error("All stock query failed: %s", e)
            return "Unable to fetch stock overview. Please check the Blood Stock page directly."

    def _get_find_donor_response(self, blood_group: Optional[str]) -> str:
        """Get donor search guidance."""
        try:
            from donors.models import Donor
            active_count = Donor.objects.filter(is_active=True).count()

            if blood_group:
                matching = Donor.objects.filter(
                    blood_group=blood_group, is_active=True
                ).count()
                return (
                    f"🔍 **Donor Search Results for {blood_group}:**\n\n"
                    f"• **{matching}** active donors with {blood_group} blood\n"
                    f"• **{active_count}** total active donors in system\n\n"
                    f"📍 **To find nearest donors:**\n"
                    f"1. Go to the ⚡ **Emergency** page\n"
                    f"2. Select **{blood_group}** as blood group\n"
                    f"3. Enter your city\n"
                    f"4. Click **Search** — AI will rank by proximity!\n\n"
                    f"📱 You can directly **Call** or **SMS** donors from results."
                )
            return (
                f"🔍 **Finding Donors:**\n\n"
                f"We have **{active_count}** active donors in the system.\n\n"
                f"To search for specific donors:\n"
                f"• Go to **Donors** page → Filter by blood group\n"
                f"• Or use **Emergency** page for proximity-based search\n\n"
                f"💡 Specify a blood group like: *\"Find A+ donors\"*"
            )
        except Exception as e:
            logger.error("Donor query failed: %s", e)
            return "Use the Donors page or Emergency page to find donors."

    def _get_statistics_response(self) -> str:
        """Get system statistics."""
        try:
            from donors.models import Donor
            from requests_management.models import BloodRequest

            total_donors = Donor.objects.count()
            active_donors = Donor.objects.filter(is_active=True).count()
            total_requests = BloodRequest.objects.count()
            pending_requests = BloodRequest.objects.filter(status='pending').count()

            return (
                f"📊 **Bloodify System Statistics:**\n\n"
                f"👥 **Donors:**\n"
                f"   • Total registered: **{total_donors}**\n"
                f"   • Currently active: **{active_donors}**\n\n"
                f"🏥 **Blood Requests:**\n"
                f"   • Total requests: **{total_requests}**\n"
                f"   • Pending: **{pending_requests}**\n\n"
                f"🤖 AI-powered donor matching is active!\n"
                f"📍 Proximity-based search using Haversine distance\n"
                f"📱 SMS notifications via Twilio integration"
            )
        except Exception as e:
            logger.error("Stats query failed: %s", e)
            return "Check the Dashboard for real-time statistics."

    # =========================================================================
    # FAQ Matching
    # =========================================================================

    def _match_faq(self, query: str) -> Tuple[Optional[FAQ], float]:
        """Match query against FAQs using keyword matching."""
        words = set(query.split())

        faqs = FAQ.objects.filter(is_active=True)
        best_match = None
        best_score = 0.0

        for faq in faqs:
            score = 0.0

            # Check keyword match
            keywords = faq.get_keywords_list()
            if keywords:
                keyword_matches = len(words.intersection(set(keywords)))
                score = keyword_matches / max(len(keywords), 1)

            # Check question similarity
            faq_words = set(faq.question.lower().split())
            word_overlap = len(words.intersection(faq_words))
            question_score = word_overlap / max(len(faq_words), 1)

            score = max(score, question_score)

            if score > best_score:
                best_score = score
                best_match = faq

        return best_match, best_score

    # =========================================================================
    # Suggestions
    # =========================================================================

    def _get_suggestions(self, intent: str) -> List[str]:
        """Get contextual follow-up suggestions."""
        suggestions_map = {
            'greeting': ["Check blood stock", "How to register?", "Am I eligible?", "Emergency request"],
            'blood_availability': ["Check another blood group", "Find nearby donors", "Blood compatibility"],
            'blood_stock_overview': ["Check A+ stock", "Check O- stock", "Find donors", "Emergency request"],
            'donor_registration': ["Eligibility criteria", "Donation process", "Benefits of donating"],
            'eligibility_info': ["Register as donor", "Donation process", "Medical conditions"],
            'emergency_info': ["Find donors", "Check stock", "Blood compatibility"],
            'blood_request_info': ["Emergency request", "Find donors", "Check availability"],
            'find_donors': ["Check blood stock", "Emergency search", "Eligibility criteria"],
            'blood_compatibility': ["Check stock", "Find donors", "Rare blood types"],
            'donation_process': ["After donation care", "Eligibility criteria", "Benefits of donating"],
            'statistics': ["Check blood stock", "Find donors", "Emergency request"],
            'about_bot': ["Check blood stock", "How to register?", "Emergency help"],
            'faq_match': ["Check blood stock", "Eligibility criteria", "Contact support"],
            'benefits': ["Donation process", "Eligibility criteria", "How often can I donate?"],
            'side_effects': ["After donation care", "Eligibility criteria", "Is it safe?"],
            'after_care': ["Benefits of donating", "How often can I donate?", "Iron levels"],
            'blood_storage': ["Blood components", "Donation process", "Check stock"],
            'blood_components': ["Blood storage", "Donation process", "Blood compatibility"],
            'rare_blood': ["Blood compatibility", "Find donors", "Check stock"],
            'donation_frequency': ["Eligibility criteria", "After donation care", "Register as donor"],
            'medical_conditions': ["Medications & donation", "Eligibility criteria", "Contact support"],
            'medications': ["Medical conditions", "Eligibility criteria", "Donation process"],
            'tattoo_piercing': ["Eligibility criteria", "Donation frequency", "Register as donor"],
            'pregnancy': ["Eligibility criteria", "Benefits of donating", "Iron levels"],
            'hemoglobin': ["Eligibility criteria", "Medical conditions", "Benefits of donating"],
            'appointment': ["Emergency search", "Find donors", "Check stock"],
            'blood_drive': ["Register as donor", "Benefits of donating", "Contact support"],
            'covid': ["Eligibility criteria", "Side effects", "Donation process"],
            'transfusion': ["Blood compatibility", "Blood components", "Emergency request"],
            'profile': ["Contact support", "Check stock", "Find donors"],
            'admin_functions': ["Check stock", "Find donors", "Show statistics"],
            'blood_disorders': ["Blood compatibility", "Find donors", "Donation frequency"],
            'system_info': ["Check stock", "Emergency search", "Show statistics"],
            'thanks': ["Check blood stock", "Find donors", "Emergency request"],
            'goodbye': ["Check blood stock", "Register as donor"],
            'contact_support': ["Check stock", "Eligibility criteria", "Emergency request"],
        }

        return suggestions_map.get(intent, [
            "Check blood stock",
            "How to register?",
            "Am I eligible?",
            "Emergency request"
        ])

