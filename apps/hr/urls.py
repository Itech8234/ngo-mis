from django.urls import path

from . import views

app_name = "hr"

urlpatterns = [
    path("departments/", views.department_list, name="department_list"),
    path("departments/new/", views.department_create, name="department_create"),
    path("departments/<int:pk>/edit/", views.department_edit, name="department_edit"),
    path("departments/<int:pk>/delete/", views.department_delete, name="department_delete"),
    # Employees
    path("employees/", views.EmployeeListView.as_view(), name="employee_list"),
    path("employees/new/", views.EmployeeCreateView.as_view(), name="employee_create"),
    path("employees/<int:pk>/", views.EmployeeDetailView.as_view(), name="employee_detail"),
    path("employees/<int:pk>/edit/", views.EmployeeUpdateView.as_view(), name="employee_edit"),
    path("employees/<int:pk>/id-card/", views.employee_id_card, name="employee_id_card"),
    path("employees/<int:pk>/id-card.pdf", views.employee_id_card_pdf, name="employee_id_card_pdf"),
    path("employees/<int:employee_pk>/documents/new/", views.employee_document_upload, name="employee_document_upload"),
    path("documents/<int:pk>/download/", views.employee_document_download, name="employee_document_download"),
    path("documents/<int:pk>/delete/", views.employee_document_delete, name="employee_document_delete"),
    path("my/documents/", views.my_documents, name="my_documents"),
    path("documents/", views.hr_document_list, name="document_list"),
    path("directory/", views.directory, name="directory"),
    path("orgchart/", views.orgchart, name="orgchart"),
    # Leave
    path("leave/", views.LeaveListView.as_view(), name="leave_list"),
    path("leave/new/", views.LeaveCreateView.as_view(), name="leave_create"),
    path("leave/<int:pk>/", views.LeaveDetailView.as_view(), name="leave_detail"),
    path("leave/<int:pk>/review/", views.leave_review, name="leave_review"),
    path("leave/<int:pk>/attachment/", views.leave_attachment_download, name="leave_attachment_download"),
    path("leave/balances/", views.leave_balances, name="leave_balances"),
    path("leave/balances/new/", views.leave_balance_create, name="leave_balance_create"),
    path("leave/balances/<int:pk>/edit/", views.leave_balance_edit, name="leave_balance_edit"),
    # Recruitment
    path("vacancies/", views.VacancyListView.as_view(), name="vacancy_list"),
    path("vacancies/new/", views.VacancyCreateView.as_view(), name="vacancy_create"),
    path("vacancies/<int:pk>/", views.VacancyDetailView.as_view(), name="vacancy_detail"),
    path("vacancies/<int:pk>/edit/", views.VacancyUpdateView.as_view(), name="vacancy_edit"),
    path("applications/<int:pk>/status/", views.application_update_status, name="application_status"),
    # Training
    path("training/", views.TrainingListView.as_view(), name="training_list"),
    path("training/new/", views.TrainingCreateView.as_view(), name="training_create"),
    path("training/<int:pk>/", views.TrainingDetailView.as_view(), name="training_detail"),
    path("training/<int:pk>/edit/", views.TrainingUpdateView.as_view(), name="training_edit"),
    # Attendance & performance
    path("attendance/", views.attendance_list, name="attendance_list"),
    path("attendance/new/", views.attendance_create, name="attendance_create"),
    path("attendance/export.csv", views.attendance_export, name="attendance_export"),
    path("attendance/<int:pk>/edit/", views.attendance_edit, name="attendance_edit"),
    path("attendance/me/", views.my_attendance, name="my_attendance"),
    path("attendance/clock/<str:action>/", views.attendance_clock, name="attendance_clock"),
    path("performance/", views.performance_list, name="performance_list"),
    path("performance/new/", views.performance_create, name="performance_create"),
    path("performance/<int:pk>/edit/", views.performance_edit, name="performance_edit"),
    path("disciplinary/", views.disciplinary_list, name="disciplinary_list"),
    path("disciplinary/new/", views.disciplinary_create, name="disciplinary_create"),
]
