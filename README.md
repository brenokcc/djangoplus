# djangoplus
An opensource extension of Django framework

## Try it!
1. Clone the project

   git clone https://github.com/brenokcc/djangoplus.git OR git clone git@github.com:brenokcc/djangoplus.git

2. Make a virtualenv

   ./djangoplus/bin/mkvirtualenv
   
   workon djangoplus
   
3. Try PetShop example

   wget http://petshop.djangoplus.net/media/petshop.zip
   
   unzip petshop.zip -d petshop
   
   cd petshop

   pip install -Ur requirements.txt
   
   runserver
   
   
## Create a project

1. Start the project

   cd ~
   
   startproject project
   
   cd project
   
2. Write your models
 
   vim project/models.py

3. Syncronize model with database

   sync
   
4. Run your project

   runserver

   
# Note

Djangoplus is in experimental phase and in constant changes. Please, don't write commercial applications with it until December 1st 2017.




