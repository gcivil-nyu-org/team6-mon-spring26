from django.shortcuts import render
from .models import CustomUser
from .forms import RegisterForm

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Get the data directly
            id_val = form.cleaned_data.get('identifier')
            pw = form.cleaned_data.get('password')
            cpw = form.cleaned_data.get('confirm_password')

            if pw == cpw:
                # Create the user manually
                user = CustomUser.objects.create(username=id_val)
                if "@" in id_val:
                    user.email = id_val
                else:
                    user.phone_number = id_val
                
                user.set_password(pw)
                user.save()
                
                print(f"SUCCESS: User {id_val} created!") # Check your terminal for this!
                return render(request, 'users/success.html', {'id_used': id_val})
            else:
                form.add_error(None, "Passwords do not match")
    else:
        form = RegisterForm()
    
    return render(request, 'users/register.html', {'form': form})