from django.urls import path
from . import views

urlpatterns = [
    # Course catalog
    path("",                                    views.list_courses,         name="list_courses"),
    path("<str:course_id>/",                    views.course_detail,        name="course_detail"),

    # Enrollment
    path("<str:course_id>/enroll/<str:user_id>/", views.enroll,             name="enroll"),
    path("enrolled/<str:user_id>/",             views.enrolled_courses,     name="enrolled_courses"),

    # Lessons
    path("lessons/<str:lesson_id>/<str:user_id>/",      views.get_lesson,           name="get_lesson"),
    path("lessons/<str:lesson_id>/complete/<str:user_id>/", views.complete_lesson,  name="complete_lesson"),

    # Assessments
    path("assessments/generate/<str:user_id>/",         views.generate_assessment,  name="generate_assessment"),
    path("assessments/<str:assessment_id>/submit/<str:user_id>/", views.submit_assessment, name="submit_assessment"),
    path("assessments/history/<str:user_id>/",          views.assessment_history,   name="assessment_history"),

    # Progress dashboard
    path("progress/<str:user_id>/",                     views.learning_progress,    name="learning_progress"),
    path("<str:course_id>/progress/<str:user_id>/modules/", views.module_progress,  name="module_progress"),
]