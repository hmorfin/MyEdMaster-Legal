from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import UserProfile
from bson import ObjectId
from rest_framework.decorators import api_view
from apps.chat.models import Conversation, TopicMastery
from .choices import (
    PROFESSION_CHOICES,
    EMPLOYMENT_TYPE_CHOICES,
    VETERAN_STATUS_CHOICES,
    DISABILITY_STATUS_CHOICES,
    MARITAL_STATUS_CHOICES,
    INCOME_BRACKET_CHOICES,
)

def validate_enum_attributes(user_attributes):
    errors = {}

    profession = user_attributes.get("profession")
    if profession is not None and profession not in PROFESSION_CHOICES:
        errors["profession"] = f"Invalid value. Allowed: {', '.join(PROFESSION_CHOICES)}"

    employment_type = user_attributes.get("employment_type")
    if employment_type is not None and employment_type not in EMPLOYMENT_TYPE_CHOICES:
        errors["employment_type"] = f"Invalid value. Allowed: {', '.join(EMPLOYMENT_TYPE_CHOICES)}"

    veteran_status = user_attributes.get("veteran_status")
    if veteran_status is not None and veteran_status not in VETERAN_STATUS_CHOICES:
        errors["veteran_status"] = f"Invalid value. Allowed: {', '.join(VETERAN_STATUS_CHOICES)}"

    disability_status = user_attributes.get("disability_status")
    if disability_status is not None and disability_status not in DISABILITY_STATUS_CHOICES:
        errors["disability_status"] = f"Invalid value. Allowed: {', '.join(DISABILITY_STATUS_CHOICES)}"

    marital_status = user_attributes.get("marital_status")
    if marital_status is not None and marital_status not in MARITAL_STATUS_CHOICES:
        errors["marital_status"] = f"Invalid value. Allowed: {', '.join(MARITAL_STATUS_CHOICES)}"

    income_bracket = user_attributes.get("income_bracket")
    if income_bracket is not None and income_bracket not in INCOME_BRACKET_CHOICES:
        errors["income_bracket"] = f"Invalid value. Allowed: {', '.join(INCOME_BRACKET_CHOICES)}"

    return errors


def user_profile_to_dict(user):
    """Build a JSON serializable dict of all UserProfile fields"""
    data = {
        "id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone or "",
        "dob": user.dob.isoformat() if user.dob else None,
        "location": user.location,
        "user_attributes": user.user_attributes,
        "onboarded": user.onboarded,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
    return data


class LoginView(APIView):
    """Look up user by email and return all user profile fields."""

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        if not email:
            return Response(
                {"status": "error", "message": "email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = UserProfile.objects.filter(email__iexact=email).first()
        if user is None:
            return Response(
                {"status": "error", "message": "No user with this email."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"status": "success", "data": user_profile_to_dict(user)},
            status=status.HTTP_200_OK,
        )


class CreateUserView(APIView):
    def post(self, request):
        user = UserProfile.objects.create(
            first_name=request.data.get('first_name'),
            last_name=request.data.get('last_name'),
            email=request.data.get('email')
        )
        return Response({
            "status": "success",
            "data": {
                "id": str(user.id),
                "onboarded": user.onboarded,
                "createdAt": user.created_at
            }
        }, status=status.HTTP_201_CREATED)

class ModifyUserView(APIView):
    def put(self, request, user_id):
        try:
            user = UserProfile.objects.get(id=user_id)

            user_attributes = request.data.get('user_attributes', user.user_attributes) or {}

            # Validate enums inside user_attributes
            enum_errors = validate_enum_attributes(user_attributes)
            if enum_errors:
                return Response(
                    {
                        "status": "error",
                        "message": "Invalid enum values in user_attributes",
                        "errors": enum_errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.first_name = request.data.get('first_name', user.first_name)
            user.last_name = request.data.get('last_name', user.last_name)
            user.phone = request.data.get('phone', user.phone)
            user.dob = request.data.get('dob', user.dob)
            user.location = request.data.get('location', user.location)
            user.user_attributes = user_attributes
            user.onboarded = True
            user.save()

            return Response(
                {"status": "success", "data": {"id": str(user.id)}},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"status": "error", "message": "User does not exist"},
                status=404,
            )
@api_view(["GET"])
def user_stats(request, user_id):
    try:
        user = UserProfile.objects.get(id=ObjectId(user_id))
    except Exception:
        return Response({"status": "error", "message": "User not found."}, status=404)

    scores = []

    # Chat scores — from FSPR profiles aggregated per legal domain
    conversations = Conversation.objects.filter(
        user=user,
        fspr_profile__isnull=False,
        legal_domain__isnull=False,
    )

    domain_fspr = {}
    for conv in conversations:
        domain = conv.legal_domain
        profile = conv.fspr_profile or {}
        if not profile:
            continue
        if domain not in domain_fspr:
            domain_fspr[domain] = []
        dim_scores = [
            profile.get(dim, {}).get("score", None)
            for dim in ["Facts", "Strategies", "Procedures", "Rationales"]
        ]
        dim_scores = [s for s in dim_scores if s is not None]
        if dim_scores:
            domain_fspr[domain].append(sum(dim_scores) / len(dim_scores))

    for domain, avg_list in domain_fspr.items():
        avg = sum(avg_list) / len(avg_list)
        score_out_of_5 = round(avg * 5, 1)
        scores.append({
            "title": domain,
            "score": score_out_of_5,
            "source": "chat",
            "detail": f"Based on {len(avg_list)} conversation(s) in {domain}.",
            "trend": "",
        })

    # Course scores — from TopicMastery
    mastery_qs = TopicMastery.objects.filter(user=user)
    for m in mastery_qs:
        scores.append({
            "title": m.topic,
            "score": round(m.mastery_level * 5, 1),
            "source": "course",
            "detail": f"Based on course activity in {m.topic}.",
            "trend": "",
        })

    return Response({"status": "success", "data": scores}, status=200)