import os
import logging
from flask import Flask, render_template, request, redirect, flash, url_for, send_from_directory,send_file
from flask_sqlalchemy import SQLAlchemy
import os
from fpdf import FPDF
from flask import Flask, render_template, redirect, url_for, request, flash,jsonify,session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, HiddenField
from wtforms.validators import InputRequired, Length, Email, Regexp
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import google.generativeai as genai
import webbrowser
from threading import Timer


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask App Configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = 'static/uploads'



# Initialize Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'




class JobSeekerProfile(db.Model):
    __tablename__ = 'job_seeker_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    profile_visibility = db.Column(db.String(20), default='Public')
    profile_url = db.Column(db.String(100), nullable=True)
    profile_summary = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(200), nullable=True)  # Path to profile picture
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), 
                         onupdate=db.func.current_timestamp())

    # Relationships
    education = db.relationship('Education', backref='profile', lazy='dynamic')
    skills = db.relationship('Skill', backref='profile', lazy='dynamic')

class Education(db.Model):
    __tablename__ = 'education'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('job_seeker_profiles.id'), nullable=False)
    degree = db.Column(db.String(100), nullable=False)
    institution = db.Column(db.String(100), nullable=False)
    graduation_date = db.Column(db.Date, nullable=False)
    gpa = db.Column(db.Float, nullable=True)

class Skill(db.Model):
    __tablename__ = 'skills'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('job_seeker_profiles.id'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    proficiency = db.Column(db.String(20), nullable=False)



class SeekerData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    education = db.Column(db.String(200), nullable=True)
    experience = db.Column(db.String(50), nullable=True)
    skills = db.Column(db.Text, nullable=True)
    resume_path = db.Column(db.String(200), nullable=False)

# Define the JobPost model (schema) for the Job Posting form
class JobPost(db.Model):
    __tablename__ = 'job_posts'  # Table name in the database

    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    employment_type = db.Column(db.String(50), nullable=False)
    salary_from = db.Column(db.Integer)
    salary_to = db.Column(db.Integer)
    job_description = db.Column(db.Text, nullable=False)
    key_responsibilities = db.Column(db.Text)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    logo_filename = db.Column(db.String(100))  # Filename of the uploaded logo image

    def __init__(self, job_title, location, employment_type, salary_from, salary_to, job_description, key_responsibilities, company_name, email, logo_filename=None):
        self.job_title = job_title
        self.location = location
        self.employment_type = employment_type
        self.salary_from = salary_from
        self.salary_to = salary_to
        self.job_description = job_description
        self.key_responsibilities = key_responsibilities
        self.company_name = company_name
        self.email = email
        self.logo_filename = logo_filename
# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), 
                         onupdate=db.func.current_timestamp())


@app.route('/add-resource', methods=['GET', 'POST'])
def add_resource():
    if request.method == 'POST':
        resource_type = request.form.get('resource_type')
        title = request.form.get('title')
        url = request.form.get('url')
        description = request.form.get('description')
        
        # Handle file upload
        image_path = None
        if 'file-upload' in request.files:
            file = request.files['file-upload']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"/{app.config['UPLOAD_FOLDER']}/{filename}"

        resource = Resource(
            resource_type=resource_type,
            title=title,
            url=url,
            description=description,
            image_path=image_path
        )
        
        try:
            db.session.add(resource)
            db.session.commit()
            flash('Resource added successfully!', 'success')
            return redirect(url_for('resources'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding resource: ' + str(e), 'error')
    
    return render_template('add_resource.html')

@app.route('/resources')
@login_required  # Ensure only logged-in users can access
def resources():
    # Log the current user's role for debugging
    logger.debug(f"Current user: {current_user.email}, Role: {current_user.role}")
    
    # Fetch resources by type
    videos = Resource.query.filter_by(resource_type='Video').all()
    books = Resource.query.filter_by(resource_type='Book').all()
    websites = Resource.query.filter_by(resource_type='Website').all()
    
    # Set is_company based on current_user.role
    is_company = current_user.role == 'company'
    logger.debug(f"is_company set to: {is_company}")
    
    return render_template('resources.html', 
                         videos=videos, 
                         books=books, 
                         websites=websites,
                         is_company=is_company)


@app.route('/edit-resource/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_resource(id):
    if current_user.role != 'company':
        flash('Only company users can edit resources', 'error')
        return redirect(url_for('resources'))
        
    resource = Resource.query.get_or_404(id)
    
    if request.method == 'POST':
        resource.resource_type = request.form.get('resource_type')
        resource.title = request.form.get('title')
        resource.url = request.form.get('url')
        resource.description = request.form.get('description')
        
        if 'file-upload' in request.files:
            file = request.files['file-upload']
            if file and allowed_file(file.filename):
                if resource.image_path and os.path.exists(resource.image_path[1:]):
                    os.remove(resource.image_path[1:])
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                resource.image_path = f"/{app.config['UPLOAD_FOLDER']}/{filename}"

        try:
            db.session.commit()
            flash('Resource updated successfully!', 'success')
            return redirect(url_for('resources'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating resource: ' + str(e), 'error')
    
    return render_template('edit_resource.html', resource=resource)

@app.route('/delete-resource/<int:id>', methods=['POST'])
@login_required
def delete_resource(id):
    if current_user.role != 'company':
        flash('Only company users can delete resources', 'error')
        return redirect(url_for('resources'))
        
    resource = Resource.query.get_or_404(id)
    try:
        if resource.image_path and os.path.exists(resource.image_path[1:]):
            os.remove(resource.image_path[1:])
        db.session.delete(resource)
        db.session.commit()
        flash('Resource deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting resource: ' + str(e), 'error')
    return redirect(url_for('resources'))
@app.route('/create-profile', methods=['GET', 'POST'])
def create_profile():
    if request.method == 'POST':
        profile = JobSeekerProfile(
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            profile_visibility=request.form.get('profile_visibility'),
            profile_url=request.form.get('profile_url'),
            profile_summary=request.form.get('profile_summary'),
            profile_picture=request.form.get('profile_picture')  # Handle file upload separately
        )
        
        # Add education
        education = Education(
            degree=request.form.get('degree'),
            institution=request.form.get('institution'),
            graduation_date=datetime.strptime(request.form.get('graduation_date'), '%Y-%m-%d'),
            gpa=float(request.form.get('gpa')) if request.form.get('gpa') else None
        )
        profile.education.append(education)

        # Add skill
        skill = Skill(
            skill_name=request.form.get('skill'),
            proficiency=request.form.get('proficiency')
        )
        profile.skills.append(skill)

        db.session.add(profile)
        db.session.commit()
        return redirect(url_for('view_profile', profile_id=profile.id))
    
    return render_template('create_profile.html')

@app.route('/profile')
@login_required
def view_profile():
    email = current_user.email
    profile = SeekerData.query.filter_by(email=email).first()
    
    if not profile:
        flash('Profile not found', 'error')
        return redirect(url_for('app_tracker'))
    
    # Generate resume URL if exists
    resume_url = None
    if profile.resume_path:
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], profile.resume_path)
        if os.path.exists(resume_path):
            resume_url = url_for('static', filename=f'uploads/{profile.resume_path}')
    
    return render_template('view_profile.html', 
                         profile=profile, 
                         email=email,
                         resume_url=resume_url)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    email = current_user.email
    profile = SeekerData.query.filter_by(email=email).first()
    
    if not profile:
        flash('Profile not found', 'error')
        return redirect(url_for('app_tracker'))
    
    # Generate resume URL if exists
    resume_url = None
    if profile.resume_path:
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], profile.resume_path)
        if os.path.exists(resume_path):
            resume_url = url_for('static', filename=f'uploads/{profile.resume_path}')
    
    if request.method == 'POST':
        try:
            # ... [rest of your existing POST handling code] ...
            return redirect(url_for('view_profile'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating profile: {str(e)}", exc_info=True)
            flash(f'Error updating profile: {str(e)}', 'error')
    
    return render_template('edit_profile.html', 
                         profile=profile, 
                         email=email,
                         resume_url=resume_url)  # Pass resume_url to template

@app.route('/applications', methods=['GET'])
def job_listings():
    employment_type = request.args.get('employment_type')
    location = request.args.get('location')
    salary_from = request.args.get('salary_from', type=int)
    salary_to = request.args.get('salary_to', type=int)

    query = JobPost.query

    if employment_type:
        query = query.filter_by(employment_type=employment_type)
    if location:
        query = query.filter(JobPost.location.ilike(f"%{location}%"))
    if salary_from is not None:
        query = query.filter(JobPost.salary_from >= salary_from)
    if salary_to is not None:
        query = query.filter(JobPost.salary_to <= salary_to)

    jobs = query.all()
    
    return render_template('applications.html', jobs=jobs)





from datetime import datetime

@app.route('/apply/<int:job_post_id>', methods=['POST'])
@login_required
def apply_for_job(job_post_id):
    """
    Apply for a job post if the user hasn't already applied.
    
    Args:
        job_post_id (int): The ID of the job post to apply for.
    
    Returns:
        Redirect to the referrer page with a flash message.
    """
    user_email = current_user.email
    user_name = current_user.name  # Assuming User model has a 'name' field

    # Check if the user has already applied
    existing_application = ActiveApplication.query.filter_by(
        seeker_email=user_email, job_post_id=job_post_id
    ).first()

    if existing_application:
        flash('You have already applied for this job.', 'warning')
        return redirect(request.referrer)

    # Fetch the job post
    job_post = JobPost.query.get(job_post_id)
    if not job_post:
        flash('Job post not found.', 'danger')
        return redirect(request.referrer)

    # Create and store new application
    new_application = ActiveApplication(
        seeker_name=user_name,
        seeker_email=user_email,
        job_post_id=job_post_id,
        job_title=job_post.job_title,
        applied_at=datetime.utcnow()  # Explicitly set for clarity
    )

    try:
        db.session.add(new_application)
        db.session.commit()
        flash('Application submitted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error applying for job {job_post_id} by {user_email}: {str(e)}")
        flash(f'Error applying for job: {str(e)}', 'danger')

    return redirect(request.referrer)


@app.route('/resumebuilder', methods=['GET', 'POST'])
def resumebuilder():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        summary = request.form.get('summary')
        style = request.form.get('style')  # User selects one of two styles

        # Generate PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        if style == "style1":
            pdf.set_text_color(50, 50, 255)
        else:
            pdf.set_text_color(0, 150, 0)

        pdf.cell(200, 10, txt=name, ln=True, align='C')
        pdf.cell(200, 10, txt=email, ln=True, align='C')
        pdf.cell(200, 10, txt=phone, ln=True, align='C')
        pdf.multi_cell(0, 10, summary)

        pdf_file = "resume.pdf"
        pdf.output(pdf_file)

        return send_file(pdf_file, as_attachment=True)

    return render_template('resumebuilder.html')



@app.route('/api/delete_job_post/<int:id>', methods=['POST'])
@login_required
def delete_job_post(id):
    """
    Delete a job post if the current user is the owner (based on email) and has the 'company' role.
    
    Args:
        id (int): The ID of the job post to delete.
    
    Returns:
        JSON response with success or error message.
    """
    # Check if the user has the 'company' role
    if current_user.role != 'company':
        return jsonify({'error': 'Unauthorized: Only company users can delete job posts'}), 403

    # Fetch the job post by ID
    job_post = JobPost.query.get_or_404(id)

    # Verify ownership using email
    if job_post.email != current_user.email:
        return jsonify({'error': 'Forbidden: You can only delete your own job posts'}), 403

    try:
        # Remove the logo file if it exists
        if job_post.logo_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], job_post.logo_filename)):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], job_post.logo_filename))

        # Delete the job post from the database
        db.session.delete(job_post)
        db.session.commit()

        return jsonify({'message': 'Job post deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting job post {id}: {str(e)}")
        return jsonify({'error': f"Failed to delete job post: {str(e)}"}), 500

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Store hashed passwords
    role = db.Column(db.String(20), nullable=False, default='seeker')
    #applications = db.Column(db.String(20),nullable=False)
# New AcceptedApplication model
class ActiveApplication(db.Model):
    __tablename__ = 'active_application'
    id = db.Column(db.Integer, primary_key=True)
    seeker_name = db.Column(db.String(100), nullable=False)  # Added for consistency
    seeker_email = db.Column(db.String(120), nullable=False)
    job_post_id = db.Column(db.Integer, db.ForeignKey('job_posts.id'), nullable=False)  # Links to JobPost
    job_title = db.Column(db.String(200), nullable=False)
    applied_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<ActiveApplication {self.job_title} for {self.seeker_email}>"

class AcceptedApplication(db.Model):
    __tablename__ = 'accepted_application'
    id = db.Column(db.Integer, primary_key=True)
    seeker_name = db.Column(db.String(100), nullable=False)
    seeker_email = db.Column(db.String(120), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    applied_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<AcceptedApplication {self.job_title} for {self.seeker_email}>"

class RejectedApplication(db.Model):
    __tablename__ = 'rejected_application'
    id = db.Column(db.Integer, primary_key=True)
    seeker_name = db.Column(db.String(100), nullable=False)
    seeker_email = db.Column(db.String(120), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    applied_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<RejectedApplication {self.job_title} for {self.seeker_email}>"







@app.route('/api/job_posts', methods=['GET'])
@login_required  # Restrict access to logged-in users only
def get_job_posts():
    try:
        # Get the email of the active logged-in user
        user_email = current_user.email
        
        # Query the job_posts table, filtering by the user's email
        job_posts = JobPost.query.filter_by(email=user_email).all()
        
        # Return the filtered job posts as JSON, including the 'id' field
        return jsonify([{
            'id': post.id,  # Added this field
            'job_title': post.job_title,
            'location': post.location,
            'employment_type': post.employment_type,
            'salary_from': post.salary_from if post.salary_from is not None else 0,
            'salary_to': post.salary_to if post.salary_to is not None else 0,
            'company_name': post.company_name,
            'email': post.email,
            'logo_filename': post.logo_filename
        } for post in job_posts])
    except Exception as e:
        logger.error(f"Error in /api/job_posts: {str(e)}")
        return jsonify({'error': str(e)}), 500





@app.route('/api/active_applications', methods=['GET'])
@login_required
def get_active_applications():
    # Get the email of the logged-in company user
    company_email = current_user.email
    
    # Fetch job posts created by the logged-in company
    company_jobs = JobPost.query.filter_by(email=company_email).all()
    job_post_ids = [job.id for job in company_jobs]  # Get IDs of the company's job posts
    
    # Fetch active applications for those job posts
    active_applications = ActiveApplication.query.filter(ActiveApplication.id.in_(job_post_ids)).all()
    
    # Fetch seeker details and prepare the response
    applications_data = []
    for app in active_applications:
        seeker = User.query.filter_by(email=app.seeker_email).first()
        job = JobPost.query.get(app.job_post_id)
        if seeker and job:
            applications_data.append({
                'seeker_name': seeker.name,
                'seeker_email': seeker.email,
                'job_title': job.job_title,
                'applied_at': app.applied_at.strftime('%Y-%m-%d %H:%M:%S'),
                'job_post_id': app.job_post_id
            })
    
    return jsonify(applications_data)






# Route for displaying and handling the form submission
@app.route('/postcreation', methods=['GET', 'POST'])
@login_required  # Restrict to logged-in users
def post_creation():
    if request.method == 'POST':
        try:
            # Collect form data
            job_title = request.form['job_title']
            location = request.form['location']
            employment_type = request.form['employment_type']
            salary_from = int(request.form['salary_from']) if request.form['salary_from'] else None
            salary_to = int(request.form['salary_to']) if request.form['salary_to'] else None
            job_description = request.form['job_description']
            key_responsibilities = request.form.get('key_responsibilities', '')  # Optional field
            company_name = request.form['company_name']
            email = current_user.email  # Use logged-in user's email
            
            # Handle logo upload (if provided)
            logo_filename = None
            if 'logo' in request.files:
                logo_file = request.files['logo']
                if logo_file and allowed_file(logo_file.filename):
                    logo_filename = secure_filename(logo_file.filename)
                    logo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], logo_filename))

            # Create a new JobPost object with the form data
            new_job_post = JobPost(
                job_title=job_title,
                location=location,
                employment_type=employment_type,
                salary_from=salary_from,
                salary_to=salary_to,
                job_description=job_description,
                key_responsibilities=key_responsibilities,
                company_name=company_name,
                email=email,
                logo_filename=logo_filename
            )

            # Add the new job post to the database and commit
            db.session.add(new_job_post)
            db.session.commit()

            # Flash a success message
            flash('Job posted successfully!', 'success')

            # Redirect to the company dashboard
            return redirect(url_for('company_dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating job post: {str(e)}")
            flash(f"Error posting job: {str(e)}", 'danger')
            return redirect(url_for('post_creation'))

    # If it's a GET request, render the template
    return render_template('postcreation.html')
# Initialize the database (create the tables if they don't exist)
with app.app_context():
    db.create_all()







class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(max=50)])
    email = StringField('Email', validators=[InputRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6, max=80)])
    role = HiddenField('Role')  # Defaults to 'seeker' if not selected
    submit = SubmitField('Register')


# Login Form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6, max=80)])
    submit = SubmitField('Login')

@app.route('/api/seeker_status', methods=['GET'])
@login_required
def seeker_status():
    user_email = current_user.email

    # Fetch accepted applications
    accepted_apps = AcceptedApplication.query.filter_by(seeker_email=user_email).all()
    accepted_data = [{
        'job_title': app.job_title,
        'applied_at': app.applied_at.strftime('%Y-%m-%d %H:%M:%S')
    } for app in accepted_apps]

    # Fetch rejected applications
    rejected_apps = RejectedApplication.query.filter_by(seeker_email=user_email).all()
    rejected_data = [{
        'job_title': app.job_title,
        'applied_at': app.applied_at.strftime('%Y-%m-%d %H:%M:%S')
    } for app in rejected_apps]

    # Fetch under review applications
    active_apps = ActiveApplication.query.filter_by(seeker_email=user_email).all()
    under_review_data = [{
        'job_title': app.job_title,
        'applied_at': app.applied_at.strftime('%Y-%m-%d %H:%M:%S')
    } for app in active_apps]

    return jsonify({
        'accepted': accepted_data,
        'rejected': rejected_data,
        'under_review': under_review_data
    })




@login_manager.user_loader
def load_user(user_id):
    logger.debug(f'Loading user with ID: {user_id}')
    return User.query.get(int(user_id))


@app.route('/')
def landing():
    return render_template('landing.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        role = form.role.data if form.role.data else "seeker"  
        
        new_user = User(name=form.name.data, email=form.email.data, password=form.password.data, role=role)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Email already exists or another error occurred.', 'danger')

    return render_template('registration.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password == form.password.data:  # Plaintext comparison (insecure, should use hashing)
            login_user(user)
            logger.debug(f"User {user.email} logged in with role: {user.role}")

            # Redirect based on user role
            if user.role == 'seeker':
                seeker_data = SeekerData.query.filter_by(email=user.email).first()
                if seeker_data:
                    return redirect(url_for('app_tracker'))  # If seeker data is present
                else:
                    return redirect(url_for('seeker_data'))  # If seeker data is not present
                
            elif user.role == 'company':
                return redirect(url_for('company_dashboard'))  # For company users
                
            else:
                flash('Unauthorized role', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)


# Route for Seeker with Data
@app.route('/apptracker')
@login_required
def app_tracker():
    return render_template('apptracker.html')


# Route for Seeker without Data
@app.route('/seekerdata')
@login_required
def seeker_data():
    return render_template('seekerdata.html')


# Route for Company
@app.route('/compapptrack')
@login_required
def company_dashboard():
    return render_template('compapptrack.html')



    

@app.route('/api/active_applications')
@login_required
def api_active_applications():
    seekers = SeekerData.query.all()  # Adjust query based on your app logic
    applications = [{
        'seeker_name': seeker.full_name,
        'seeker_email': seeker.email,
        'job_title': 'Sample Job',  # Replace with actual job title if linked
        'applied_at': '2023-10-01'  # Replace with actual timestamp if available
    } for seeker in seekers]
    return jsonify(applications)





@app.route('/api/accept', methods=['POST'])
@login_required
def api_accept():
    data = request.get_json()
    seeker_email = data.get('email')

    if not seeker_email:
        return jsonify({'error': 'Email is required'}), 400

    application = ActiveApplication.query.filter_by(seeker_email=seeker_email).first()

    if application:
        new_accepted = AcceptedApplication(
            seeker_name=application.seeker_name,
            seeker_email=application.seeker_email,
            job_title=application.job_title,
            applied_at=application.applied_at
        )
        db.session.add(new_accepted)
        db.session.delete(application)  # Remove from ActiveApplication
        db.session.commit()

        flash('Application Accepted Successfully!', 'success')  # ✅ Flash message added
        return jsonify({'message': 'Application accepted'}), 200
    
    return jsonify({'error': 'Application not found'}), 404


@app.route('/api/reject', methods=['POST'])
@login_required
def api_reject():
    """
    Reject an active application and move it to RejectedApplication.
    
    Returns:
        JSON response indicating success or failure.
    """
    data = request.get_json()
    seeker_email = data.get('email')

    if not seeker_email:
        return jsonify({'error': 'Email is required'}), 400

    # Query using seeker_email instead of user_email
    application = ActiveApplication.query.filter_by(seeker_email=seeker_email).first()

    if application:
        new_rejected = RejectedApplication(
            seeker_name=application.seeker_name,  # Use the seeker_name from ActiveApplication
            seeker_email=application.seeker_email,
            job_title=application.job_title,
            applied_at=application.applied_at
        )
        db.session.add(new_rejected)
        db.session.delete(application)  # Remove from ActiveApplication
        db.session.commit()

        flash('Application Rejected Successfully!', 'danger')
        return jsonify({'message': 'Application rejected'}), 200
    
    return jsonify({'error': 'Application not found'}), 404



@app.route('/api/remove_active/<email>', methods=['DELETE'])
@login_required
def remove_active(email):
    # This route is redundant since we're already deleting in accept/reject
    # But we'll add it for compatibility with your JavaScript
    return jsonify({'message': 'Application removed from active list'}), 200





@app.route('/api/seeker_status', methods=['GET'])
def get_application_status():
    active_email = request.args.get('email')  # Get the active user's email

    # Fetch applications based on the email
    accepted_apps = AcceptedApplication.query.filter_by(seeker_email=active_email).all()
    rejected_apps = RejectedApplication.query.filter_by(seeker_email=active_email).all()
    under_review_apps = ActiveApplication.query.filter_by(user_email=active_email).all()

    # Convert data to JSON
    data = {
        "accepted": [
            {"job_title": app.job_title, "applied_at": app.applied_at.strftime('%Y-%m-%d')}
            for app in accepted_apps
        ],
        "rejected": [
            {"job_title": app.job_title, "applied_at": app.applied_at.strftime('%Y-%m-%d')}
            for app in rejected_apps
        ],
        "under_review": [
            {"job_title": app.job_title, "applied_at": app.applied_at.strftime('%Y-%m-%d')}
            for app in under_review_apps
        ]
    }

    return jsonify(data)






@app.route('/apptracker')
@login_required
def apptracker():
    logger.debug(f'User {current_user.email} accessed dashboard')
    # Fetch all seeker data entries
    seekers = SeekerData.query.all()
    return render_template('apptracker.html', seekers=seekers)

#restaurant_dashboard Route (Protected)
# Replace "YOUR_API_KEY_HERE" with your actual Google Generative AI API key
genai.configure(api_key="AIzaSyBkCxP-RwWc4-qqBfFvJ9HKxlBLlgN4g2w")

# Configuration for the AI model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Initialize the AI model
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

def GenerateResponse(input_text):
    """
    Generate a response from the AI model based on user input.
    """
    response = model.generate_content([
        "input: who are you",
        "output: I am an AI Agent chatbot",
        "input: What all can you do?",
        "output: I can help you with few instructions to get-rid of problems faced in this website.",
        f"input: {input_text}",
        "output: ",
    ])
    return response.text

@app.route('/chatbot')
def chatbot():
    """Serve the chatbot page."""
    return render_template('chatbot.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages and return AI responses."""
    user_message = request.form['message']
    bot_response = GenerateResponse(user_message)
    return jsonify({'response': bot_response})


@app.route('/view_resume/<email>')
def view_resume(email):
    # Query the resume path from seeker_data table by email
    seeker = SeekerData.query.filter_by(email=email).first()
    if seeker and seeker.resume_path:
        return send_file(seeker.resume_path, as_attachment=False)  # Serve the file inline (not as download)
    else:
        flash('Resume not found', 'danger')
        return redirect(url_for('apptracker'))








@app.route("/compapptrack", methods=["POST","GET"])
def compapptrack():
    

    return render_template('compapptrack.html')
    
# Cart Route (Protected)
@app.route('/createpro')
@login_required
def createpro():
    logger.debug(f'User {current_user.email} accessed cart')
    return render_template('createpro.html', user=current_user)


# Delete Address Route (Protected)
@app.route('/jobpreview')
@login_required
def jobpreview():
    logger.debug(f'User {current_user.email} accessed del_address')
    return render_template('jobpreview.html',user=current_user)

@app.route('/Lettergenerator')
@login_required
def Lettergenerator():
    logger.debug(f'User {current_user.email} accessed payment')
    return render_template('Lettergenerator.html',user=current_user)

@app.route('/mcq')
@login_required
def mcq():
    logger.debug(f'User {current_user.email} accessed delivery_tracking')
    return render_template('mcq.html',user=current_user)




@app.route('/testimonial')
def testimonial():
    return render_template('testimonial.html')



@app.route('/logout')
@login_required
def logout():
    logger.info(f'User {current_user.email} logged out')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))








@app.route('/seekerdata', methods=['GET', 'POST'])
def seekerdata_route():
    if request.method == 'POST':
        # Get form data
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        education = request.form.get('education', '')  # Optional field
        experience = request.form.get('experience', '')  # Optional field
        skills = request.form.get('skills', '')  # Optional field
        resume = request.files['resume']

        # Save resume file
        resume_filename = secure_filename(resume.filename)
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
        resume.save(resume_path)

        # Create new SeekerData entry
        seeker_entry = SeekerData(
            full_name=full_name,
            email=email,
            phone=phone,
            education=education,
            experience=experience,
            skills=skills,
            resume_path=resume_path
        )

        # Add to database and commit
        db.session.add(seeker_entry)
        db.session.commit()

        # Flash success message and redirect to /apptracker
        flash('Bio data submitted successfully!', 'success')
        return redirect(url_for('apptracker'))

    # For GET request, render seekerdata.html
    return render_template('seekerdata.html')


@app.route('/generate_offer_letter', methods=['GET'])
@login_required
def generate_offer_letter():
    job_title = request.args.get('job_title')
    applied_at = request.args.get('applied_at')
    
    # Create a PDF offer letter
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Offer Letter", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Dear Candidate,", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, txt=f"Congratulations! You have been offered the position of {job_title}.", ln=True)
    pdf.cell(200, 10, txt=f"Application Date: {applied_at}", ln=True)
    pdf.cell(200, 10, txt="We are excited to have you join our team!", ln=True)

    # Define a file name for the offer letter
    file_name = f"offer_letter_{job_title.replace(' ', '_')}_{applied_at.replace(':', '-').replace(' ', '_')}.pdf"
    pdf_file_path = f"./{file_name}"
    
    # Save the PDF to a temporary path
    pdf.output(pdf_file_path)

    # Send the PDF file for download
    return send_file(pdf_file_path, as_attachment=True, download_name=file_name)

@app.route('/api/company_application_status', methods=['GET'])
@login_required
def company_application_status():
    company_email = current_user.email

    # Fetch job posts created by the company
    company_jobs = JobPost.query.filter_by(email=company_email).all()
    job_titles = [job.job_title for job in company_jobs]

    # Fetch accepted applications for the company's job posts
    accepted_apps = AcceptedApplication.query.filter(AcceptedApplication.job_title.in_(job_titles)).all()
    accepted_data = [{
        'seeker_name': app.seeker_name,
        'seeker_email': app.seeker_email,
        'job_title': app.job_title,
        'applied_at': app.applied_at.strftime('%Y-%m-%d %H:%M:%S')
    } for app in accepted_apps]

    # Fetch rejected applications for the company's job posts
    rejected_apps = RejectedApplication.query.filter(RejectedApplication.job_title.in_(job_titles)).all()
    rejected_data = [{
        'seeker_name': app.seeker_name,
        'seeker_email': app.seeker_email,
        'job_title': app.job_title,
        'applied_at': app.applied_at.strftime('%Y-%m-%d %H:%M:%S')
    } for app in rejected_apps]

    return jsonify({
        'accepted_applications': accepted_data,
        'rejected_applications': rejected_data
    })
@app.route('/edit_job_post/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job_post(job_id):
    # Fetch the job post by ID and ensure it belongs to the current user
    job = JobPost.query.filter_by(id=job_id, email=current_user.email).first_or_404()

    if request.method == 'POST':
        try:
            # Update job post fields
            job.job_title = request.form['job_title']
            job.location = request.form['location']
            job.employment_type = request.form['employment_type']
            job.salary_from = int(request.form['salary_from']) if request.form['salary_from'] else None
            job.salary_to = int(request.form['salary_to']) if request.form['salary_to'] else None
            job.job_description = request.form['job_description']
            job.key_responsibilities = request.form.get('key_responsibilities', '')
            job.company_name = request.form['company_name']
            job.email = request.form['email']

            # Handle logo update
            if 'logo' in request.files:
                logo_file = request.files['logo']
                if logo_file and allowed_file(logo_file.filename):
                    logo_filename = secure_filename(logo_file.filename)
                    logo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], logo_filename))
                    job.logo_filename = logo_filename  # Update logo if a new one is uploaded

            db.session.commit()
            flash('Job post updated successfully!', 'success')
            return redirect(url_for('company_dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating job post {job_id}: {str(e)}")
            flash(f"Error updating job: {str(e)}", 'danger')
            return redirect(url_for('edit_job_post', job_id=job_id))

    # For GET request, render the form with the job data
    return render_template('postcreation.html', job=job)





# Create Database Tables if They Don't Exist
if __name__ == '__main__':
    if not os.path.exists("users.db"):
        with app.app_context():
            db.create_all()
            logger.info('Database initialized successfully!')
    logger.info('Starting Flask application...')
    app.run(debug=True)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Ensure that you bind to the correct port in Heroku
    port = int(os.environ.get('PORT', 5000))  # Use the PORT environment variable for Heroku
    app.run(host='0.0.0.0', port=port, debug=False)



