from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
# Create your views here.
from dotenv import load_dotenv
import os
from openai import OpenAI
import openai
from .models import ChatGptBot
load_dotenv()
from django.contrib.auth import authenticate, login
from django.views.generic import CreateView, DeleteView, FormView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import SignUpForm, UserLoginForm
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from .forms import UploadFileForm
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from .forms import UploadFileForm

import pandas as pd
import os
import json
from pandas import json_normalize
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import io


client = OpenAI(
    # This is the default and can be omitted
    api_key=os.getenv("OPENAI_API_KEY"),
)


class HomeView(LoginRequiredMixin, ListView):
    model = ChatGptBot
    template_name = 'index.html'
    context_object_name = 'get_history'

    def get_queryset(self):
        return ChatGptBot.objects.filter(user=self.request.user)

    # 1. **read_data**: Handles reading various file types based on the file extension (csv, excel, json, etc.)
    def read_data(self, file_path):
        extension = os.path.splitext(file_path)[1].lower().lstrip('.')
        
        if extension == 'csv':
            df = pd.read_csv(file_path)
        elif extension == 'xlsx':
            df = pd.read_excel(file_path)
        elif extension == 'xml':
            df = pd.read_xml(file_path)
        elif extension == 'json':
            with open(file_path, 'r') as f:
                data = json.load(f)
            df = json_normalize(data)
        elif extension == 'parquet':
            df = pd.read_parquet(file_path)
        elif extension == 'orc':
            df = pd.read_orc(file_path)
        else:
            raise ValueError(f"Unsupported file type: {extension}")
        
        print(f"Data preview for {file_path}:")
        print(df.head(5))
        print("\n")
        print(f"Data columns and data types for {file_path}:")
        print(df.dtypes)    
        print("\n")
        return df

    # 2. **show_preview**: Returns the preview of the uploaded file (first 5 rows)
    def show_preview(self, file_path):
        df = self.read_data(file_path)
        preview_data = df.head(5).to_html(classes='table table-striped')
        return preview_data

    # 3. **show_column_types**: Returns the column types for the uploaded file
    def show_column_types(self, file_path):
        df = self.read_data(file_path)
        column_types = df.dtypes.to_string()
        return column_types

    # 4. **show_null_values**: Returns the null value count for each column in the uploaded file
    def show_null_values(self, file_path):
        df = self.read_data(file_path)
        null_values = df.isnull().sum().to_string()
        return null_values

    # 5. **show_info**: Returns basic information about the DataFrame
    def show_info(self, file_path):
        df = self.read_data(file_path)
        buffer = io.StringIO()
        df.info(buf=buffer)
        info = buffer.getvalue()
        return info

    # 6. **show_describe**: Returns descriptive statistics of the DataFrame
    def show_describe(self, file_path):
        df = self.read_data(file_path)
        describe = df.describe().to_string()
        return describe
        
    # 7. **handle_uploaded_file**: Handles file upload, saving it to the server, and stores its path in the session
    def handle_uploaded_file(self, request, f):
        path = default_storage.save(f.name, ContentFile(f.read()))  # **Change 1**: Added file saving to storage
        file_path = os.path.join(default_storage.location, path)
        request.session['current_file'] = file_path  # **Change 2**: Storing file path in session for later use
        return file_path
    
    # 8. **file**: Handles POST requests for different actions like file upload and data preview
    def file(self, request):
        preview_data = None
        column_types = None
        null_values = None
        info = None
        describe = None
        error_message = None
        current_file = request.session.get('current_file')

        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                action = request.POST.get('action')  # **Change 3**: Get the action from the form submission

                if action == 'upload' and 'file' in request.FILES:  # **Change 4**: Handle file upload action
                    try:
                        current_file = self.handle_uploaded_file(request, request.FILES['file'])
                        messages.success(request, f"File '{request.FILES['file'].name}' uploaded successfully!")  # Success message
                    except Exception as e:
                        error_message = f"Error processing file: {e}"

                elif action == 'show_preview' and current_file:  # **Change 5**: Handle showing file preview
                    preview_data = self.show_preview(current_file)

                elif action == 'show_column_type' and current_file:  # **Change 6**: Handle showing column types
                    column_types = self.show_column_types(current_file)

                elif action == 'show_null_values' and current_file:  # **Change 7**: Handle showing null value summary
                    null_values = self.show_null_values(current_file)

                elif action == 'show_info' and current_file:  # **Change 8**: Handle showing DataFrame info
                    info = self.show_info(current_file)

                elif action == 'show_describe' and current_file:  # **Change 9**: Handle showing describe statistics
                    describe = self.show_describe(current_file)

                else:
                    error_message = "Invalid file or action."

                return render(request, 'index.html', {  # **Change 10**: Returning the updated data to the template
                    'form': form,
                    'preview_data': preview_data,
                    'column_types': column_types,
                    'null_values': null_values,
                    'info': info,
                    'describe': describe,
                    'error_message': error_message,
                    'current_file': current_file
                })
        else:
            form = UploadFileForm()  # **Change 11**: Creating an empty form for the first GET request

        return render(request, 'index.html', {'form': form, 'preview_data': preview_data, 'column_types': column_types, 'null_values': null_values, 'info': info, 'describe': describe, 'error_message': error_message, 'current_file': current_file})

    # 9. **post**: Handles button actions for file uploads and chatbot interactions
    def post(self, request, *args, **kwargs):
        if 'upload-btn' in request.POST:
            # Handle the file upload when the button is clicked
            uploaded_file = request.FILES.get('uploaded_file')
            if uploaded_file:
                file_path = self.handle_uploaded_file(request, uploaded_file)
                # After uploading, display the file details or preview
                messages.success(request, f"File '{uploaded_file.name}' uploaded successfully!")
            else:
                messages.error(request, "No file uploaded.")
        elif 'btn' in request.POST:  # **Change 13**: Trigger chatbot interaction
            user_input = request.POST.get('userInput')
            clean_user_input = str(user_input).strip()
            if clean_user_input:
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "user",
                                "content": clean_user_input,
                            }
                        ],
                    )
                    bot_response = response.choices[0].message.content
                    ChatGptBot.objects.create(
                        user=request.user,
                        messageInput=clean_user_input,
                        bot_response=bot_response,
                    )
                except openai.APIConnectionError as e:
                    messages.warning(request, f"Failed to connect to OpenAI API, check your internet connection")
                except openai.RateLimitError as e:
                    messages.warning(request, f"You exceeded your current quota, please check your plan and billing details.")
        
        return redirect(request.META['HTTP_REFERER'])  # **Change 14**: Redirect back to the previous page after action


# Other classes for signup, login, etc., remain unchanged.




class SignUp(CreateView):
    form_class = SignUpForm
    template_name = "users/register.html"
    def form_valid(self, form):
        response = super().form_valid(form)
        # Get the user's username and password in order to automatically authenticate user after registration
        username = form.cleaned_data['username']
        password = form.cleaned_data['password1']
        # Authenticate the user and log him/her in
        user = authenticate(username=username, password=password)
        login(self.request, user)
        return response
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.warning(self.request, f"{field}: {error}")
        return redirect(self.request.META['HTTP_REFERER'])
    def get_success_url(self):
        return reverse("main")



class LoginView(FormView):
    form_class = UserLoginForm
    template_name = "login.html"
    def form_valid(self, form):
        response = super().form_valid(form)
        # Get the user's username and password and authenticate
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        # Authenticate the user and log him/her in
        user = authenticate(username=username, password=password)
        login(self.request, user)
        messages.success(self.request, "You are logged in")
        return response
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.warning(self.request, f"{error}")
        return redirect(self.request.META['HTTP_REFERER'])
    def get_success_url(self):
        return reverse("main")



@login_required
def DeleteHistory(request):
    chatGptobjs = ChatGptBot.objects.filter(user = request.user)
    chatGptobjs.delete()
    messages.success(request, "All messages have been deleted")
    return redirect(request.META['HTTP_REFERER'])


def logout_view(request):
    logout(request)
    messages.success(request, "Succesfully logged out")
    return redirect("main")