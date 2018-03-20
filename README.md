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

# Used Libraries

| Livrary   | License | Attribuition |
|-----------|---------|--------------|
|Bootstrap|MIT|Twitter|
|Chartist|MIT|Gion Kunz|
|Dage Range Picker|MIT|Dan Grossman|
|Fontawsome|GPL|Dave Gandy|
|FullCalendar|MIT|Adam Shaw|
|jQuery|MIT|JS Foundation and other contributors|
|JQuery Toask|MIT|Kamran Ahmed|
|jQuery Cookie Plugin|MIT|Klaus Hartl|
|jQuery Mask Plugin|MIT|Igor Escobar|
|jQuery Popup Overlay|MIT|HubSpot, Inc|
|jQuery treegrid Plugin|MIT|Pomazan Max|
|Momentjs|MIT|Tim Wood, Iskren Chernev, Moment.js contributors|
|MetisMenu|MIT|Osman Nuri Okumus|
|Select2|MIT|Kevin Brown, Igor Vaynberg, and Select2 contributors|
|VelocityJS|MIT|Julian Shapiro|
|TinyMCE |GNU|Free Software Foundation, Inc|



