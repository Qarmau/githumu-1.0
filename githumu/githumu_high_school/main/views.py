# Django Built-in Modules
from django.contrib.auth import logout, login, authenticate
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, FileResponse
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Min
from django.utils import timezone
from django.core.paginator import Paginator
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages

# Django Forms
from django.contrib.auth.forms import AuthenticationForm

# Project-Specific Imports
from .models import *
from .forms import (ContactForm,
    CustomUserCreationForm,
    HolidayAssignmentForm,
    UserProfileForm, 
    TeacherProfileForm,
    AdministratorProfileForm
)

def download_assignment(request, assignment_id):
    assignment = get_object_or_404(HolidayAssignment, id=assignment_id)
    assignment.download_count += 1
    assignment.save()
    return FileResponse(assignment.file, as_attachment=True)

# Home page view
def home(request):
    current_time = timezone.now()
    events = Event.objects.filter(date__gte=current_time).order_by('date')[:3]
    news = News.objects.order_by('-date')[:5]
    calendar_events = CalendarEvent.objects.filter(date__gte=current_time).order_by('date')[:10]

    context = {
        'events': events,
        'news': news,
        'calendar_events': calendar_events,
    }
    return render(request, 'home.html', context)

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'event_detail.html', {'event': event})

# About page view
def about(request):
    about_info = About.objects.first()

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            send_mail(
                f'Message from {name}',
                message,
                email,
                [about_info.email],
                fail_silently=False,
            )
            messages.success(request, 'Your message has been sent successfully!')
        else:
            messages.error(request, 'There was an error with your submission. Please check the form and try again.')
    else:
        form = ContactForm()
    return render(request, 'about.html', {'about': about_info, 'form': form})

# Administration page view
def administration(request):
    administrators = Administrator.objects.all().order_by('order')
    return render(request, 'administration.html', {'administrators': administrators})

# Teaching staff page view
def teaching_staff(request):
    staff = TeachingStaff.objects.all().order_by('order')
    return render(request, 'teaching_staff.html', {'staff': staff})

# Achievements page view
def achievements(request):
    university_admissions = Achievement.objects.all().order_by('year')
    awards = CoCurricularAward.objects.all().order_by('-year')
    return render(request, 'achievements.html', {
        'university_admissions': university_admissions,
        'awards': awards,
    })

# Academics page view
def academics(request):
    assignments = HolidayAssignment.objects.all().order_by('-date_uploaded')

    # Extract unique years
    unique_academics = []
    unique_years = set()
    for assignment in assignments:
        if assignment.year not in unique_years:
            unique_academics.append(assignment)
            unique_years.add(assignment.year)

    return render(request, 'academics.html', {'academics': unique_academics})

def likizo(request):
    assignments = HolidayAssignment.objects.all().order_by('-date_uploaded')

    # Extract unique years
    unique_academics = []
    unique_years = set()
    for assignment in assignments:
        if assignment.year not in unique_years:
            unique_academics.append(assignment)
            unique_years.add(assignment.year)

    return render(request, 'likizo.html', {'academics': unique_academics})

def keys(request):
    return render(request,'keys.html')

# Holiday assignment detail view
def holiday(request, holiday_id):
    holiday = get_object_or_404(HolidayAssignment, id=holiday_id)
    all_assignments = HolidayAssignment.objects.filter(year=holiday.year).order_by('-date_uploaded')
    unique_assignments = {assignment.title: assignment for assignment in all_assignments}
    filtered_assignments = list(unique_assignments.values())
    return render(request, 'holiday.html', {'holiday': holiday, 'assignments': filtered_assignments})

# Grades view
def grades(request, grade_id):
    selected_assignment = get_object_or_404(HolidayAssignment, id=grade_id)
    assignments = HolidayAssignment.objects.filter(title=selected_assignment.title).order_by('-date_uploaded')
    all_grades = HolidayAssignment.objects.filter(title=selected_assignment.title).values('grade').annotate(first_assignment_id=Min('id'))
    return render(request, 'grades.html', {'grades': selected_assignment, 'assignments': assignments, 'all_grades': all_grades})

# Years view
def years(request, years_id):
    year_assignment = get_object_or_404(HolidayAssignment, id=years_id)
    return render(request, 'years.html', {'years': year_assignment})

# News detail view
def news_detail(request, news_id):
    news = get_object_or_404(News, id=news_id)
    return render(request, 'news_detail.html', {'news': news})

# Assignments view
def assignments(request, assignment_id):
    assignment = get_object_or_404(HolidayAssignment, id=assignment_id)
    related_assignments = HolidayAssignment.objects.filter(
        year=assignment.year,
        grade=assignment.grade,
        title=assignment.title
    ).order_by('subject')
    return render(request, 'assignments.html', {
        'assignment': assignment,
        'related_assignments': related_assignments,
    })

# Search view
def search(request):
    query = request.GET.get('q')
    results = []
    if query:
        results = HolidayAssignment.objects.filter(
            Q(title__icontains=query) |
            Q(grade__icontains=query) |
            Q(subject__icontains=query) |
            Q(year__icontains=query) |
            Q(file__icontains=query)
        )

        # Get the list of searches from the session
        searches = request.session.get('searches', [])

        # Add the new search query to the list
        if query not in searches:
            searches.append(query)
            # Keep only the last 5 searches
            if len(searches) > 5:
                searches.pop(0)

        # Save the updated list back to the session
        request.session['searches'] = searches

    return render(request, 'search_results.html', {'results': results, 'query': query, 'searches': request.session.get('searches', [])})


# Admin dashboard view
@login_required
def admin_dashboard(request):
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        if request.user.user_type == 'teacher':
            profile_form = TeacherProfileForm(request.POST, request.FILES, instance=request.user.teachingstaff)
        else:
            profile_form = AdministratorProfileForm(request.POST, request.FILES, instance=request.user.administrator)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('admin_dashboard')
    else:
        user_form = UserProfileForm(instance=request.user)
        if request.user.user_type == 'teacher':
            profile_form = TeacherProfileForm(instance=request.user.teachingstaff)
        else:
            profile_form = AdministratorProfileForm(instance=request.user.administrator)
    return render(request, 'admin_dashboard.html', {'user_form': user_form, 'profile_form': profile_form})

# User registration view
def register(request):
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        user_type = request.POST.get('user_type')

        if user_type == 'administrator':
            profile_form = AdministratorProfileForm(request.POST, request.FILES)
        else:
            profile_form = TeacherProfileForm(request.POST, request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)

            # Determine if the user is a superuser and adjust `is_active`
            user.is_staff = (user_type == 'administrator')
            if user.is_superuser:
                user.is_active = True  # Superusers are active by default
            else:
                user.is_active = False  # Set other users as inactive by default

            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()

            # Send email to the superuser for approval if the user is not a superuser
            if not user.is_superuser:
                send_approval_notification(user)
                messages.success(request, 'Your registration is pending approval by the administrator. You will be notified when your account is activated.')
                return redirect('login')
            else:
                messages.success(request, 'Your account has been created successfully and is active.')
                return redirect('login')
    else:
        user_form = CustomUserCreationForm()

    # Initialize forms for the GET request or in case of a POST request failure
    administrator_profile_form = AdministratorProfileForm()
    teacher_profile_form = TeacherProfileForm()

    # For POST requests that fail validation, we need to return the appropriate form
    if request.method == 'POST':
        if user_type == 'administrator':
            profile_form = AdministratorProfileForm(request.POST, request.FILES)
        else:
            profile_form = TeacherProfileForm(request.POST, request.FILES)

        return render(request, 'registration.html', {
            'user_form': user_form,
            'administrator_profile_form': profile_form if user_type == 'administrator' else administrator_profile_form,
            'teacher_profile_form': profile_form if user_type != 'administrator' else teacher_profile_form
        })

    return render(request, 'registration.html', {
        'user_form': user_form,
        'administrator_profile_form': administrator_profile_form,
        'teacher_profile_form': teacher_profile_form
    })




def send_approval_notification(user):
    subject = f"Approval Request: New User Registration - {user.username}"
    message = (
        f"Dear Administrator,\n\n"
        f"A new user has recently registered on the website. "
        f"Please review the registration details to approve the account at githumuhigh.com.\n\n"
        f"Username: {user.username}\n\n"
        f"Thank you for your prompt attention to this matter.\n\n"
        f"Best regards,\n"
        f"GHS Team"
    )
    from_email = "kamauj613@gmail.com"
    to_email = "kamaumbaya8@gmail.com"
    send_mail(subject, message, from_email, [to_email], fail_silently=False)


# User login view
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('holiday_assignment_list')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# Holiday assignment list view
@login_required
def holiday_assignment_list(request):
    
    return render(request, 'holiday_assignments.html')

# Create holiday assignment view
@login_required
def holiday_assignment_create(request):
    if request.method == 'POST':
        form = HolidayAssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.author = request.user
            assignment.save()
            response_data = {'success': True}
        else:
            response_data = {'success': False, 'errors': form.errors}
        return JsonResponse(response_data)
    else:
        form = HolidayAssignmentForm()
    return render(request, 'holiday_assignment_form.html', {'form': form})


# Delete holiday assignment view
@login_required
def holiday_assignment_delete(request, pk):
    assignment = get_object_or_404(HolidayAssignment, pk=pk)
    if request.method == 'POST':
        assignment.delete()
        return redirect('holiday_assignment_list')
    return render(request, 'holiday_assignment_delete.html', {'assignment': assignment})

# Download holiday assignment file view
@login_required
def holiday_assignment_download(request, pk):
    assignment = get_object_or_404(HolidayAssignment, pk=pk)
    response = HttpResponse(assignment.file, content_type='application/force-download')
    response['Content-Disposition'] = f'attachment; filename="{assignment.title}.{assignment.file.name.split(".")[-1]}"'
    return response

# Assignment detail view
@login_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(HolidayAssignment, pk=pk)
    if request.user.user_type == 'teacher' and assignment.author != request.user:
        return HttpResponseForbidden("You are not allowed to view this assignment.")
    return render(request, 'holiday_assignment_detail.html', {'assignment': assignment})

# Logout function
@login_required
def logout_user(request):
    logout(request)
    return redirect('login')


def password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            user = form.user
            user.password_reset_token = default_token_generator.make_token(user)
            user.password_reset_token_expiration = timezone.now() + timedelta(hours=24)
            user.password_reset_token_expiration = timezone.now() + timedelta(minutes=15)
            user.save()

            # Send password reset email
            subject = 'Password Reset Request'
            message = render_to_string('password_reset_email.html', {
                'user': user,
                'token': user.password_reset_token,
                'expiration_time': user.password_reset_token_expiration,
            })
            from_email = 'your_school@example.com'
            recipient_list = [user.email]
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)

            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()

    return render(request, 'password_reset.html', {'form': form})

def password_reset_done(request):
    return render(request, 'password_reset_done.html')

def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = CustomUserCreationForm(request.POST, instance=user)
            if form.is_valid():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.password_reset_token = ''
                user.password_reset_token_expiration = None
                user.is_active = True
                user.save()
                login(request, user)
                return redirect('home')
        else:
            form = CustomUserCreationForm(instance=user)
        return render(request, 'password_reset_confirm.html', {'form': form})
    else:
        return render(request, 'password_reset_confirm.html', {'form': None, 'error': 'The password reset link is invalid or has expired.'})

def download_assignment(request, assignment_id):
    assignment = get_object_or_404(HolidayAssignment, id=assignment_id)
    assignment.download_count += 1
    assignment.save()
    return FileResponse(assignment.file, as_attachment=True)




# gallery view
def gallery(request):
    gallery = Gallery.objects.all().order_by('-date_uploaded')
    categories = Gallery.CATEGORY_CHOICES
    return render(request, 'gallery.html', {'gallery': gallery, 'categories': categories})


#academic views
def past_papers(request):
    years = AcademicYear.objects.all()
    terms = Term.objects.all()
    grades = Grade.objects.all()
    subjects = Subject.objects.all()

    year = request.GET.get('year')
    term = request.GET.get('term')
    grade = request.GET.get('grade')
    subject = request.GET.get('subject')

    papers = PastPaper.objects.all()

    if year:
        papers = papers.filter(year__year=year)
    if term:
        papers = papers.filter(term__id=term)
    if grade:
        papers = papers.filter(grade__id=grade)
    if subject:
        papers = papers.filter(subject__id=subject)

    paginator = Paginator(papers, 12)  # Show 12 papers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'years': years,
        'terms': terms,
        'grades': grades,
        'subjects': subjects,
    }

    return render(request, 'past_papers.html', context)

def revision_materials(request):
    years = AcademicYear.objects.all()
    terms = Term.objects.all()
    grades = Grade.objects.all()
    subjects = Subject.objects.all()

    year = request.GET.get('year')
    term = request.GET.get('term')
    grade = request.GET.get('grade')
    subject = request.GET.get('subject')

    materials = RevisionMaterial.objects.all()

    if year:
        materials = materials.filter(year__year=year)
    if term:
        materials = materials.filter(term__id=term)
    if grade:
        materials = materials.filter(grade__id=grade)
    if subject:
        materials = materials.filter(subject__id=subject)

    paginator = Paginator(materials, 12)  # Show 12 materials per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'years': years,
        'terms': terms,
        'grades': grades,
        'subjects': subjects,
    }

    return render(request, 'revision_materials.html', context)

#uploading exams and revision
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import PastPaperForm, RevisionMaterialForm

@login_required
def upload_past_paper(request): 
    if request.method == 'POST':
        form = PastPaperForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('holiday_assignment_list')
    else:
        form = PastPaperForm()
    return render(request, 'upload_past_paper.html', {'form': form})

@login_required
def upload_revision_material(request):
    if request.method == 'POST':
        form = RevisionMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('holiday_assignment_list')
    else:
        form = RevisionMaterialForm()
    return render(request, 'upload_revision_material.html', {'form': form})