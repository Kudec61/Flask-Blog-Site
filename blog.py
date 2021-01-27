import re
from types import resolve_bases
from MySQLdb.cursors import CursorStoreResultMixIn
from flask import Flask, render_template,redirect,flash,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField, form,validators
from passlib.hash import sha256_crypt
from functools import wraps # decoratör kontrolü için
from flask_wtf import FlaskForm


# kulanıcı giriş decoratörü
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "login" in session:
            return f(*args, **kwargs)
        else:
            flash("Sayfayı görüntülemek için giriş yapabilirsiniz.!","danger")
            return redirect(url_for("login"))
    return decorated_function
        

app = Flask(__name__)
app.secret_key = "gb_blog"



# flask'ı mySQL veri tabanına bağlamak
app.config["MYSQL_HOST"] = "localhost"  # veri tabanı adresi ( çalıştırılacağı host)
app.config["MYSQL_USER"] = "root" # kulanıcı root kök dizininde olduğu için bu dosya adı yazılıyor.
app.config["MYSQL_PASSWORD"] = "" # varsayılan olarak parola boş gelecektir.
app.config["MYSQL_DB"] = "gb_blog"  # veritabanı adı
app.config["MYSQL_CURSORCLASS"] = "DictCursor" # veritabanından verileri sözlük olarak alabilmek için

mysql = MySQL(app) # uygulamayı veritabanına bağlamak için

# Kullanıcı kayıt formu oluşturuluyor
class registerForm(Form):
    name = StringField(label="",validators=[validators.length(max=25,min=3,message="Minimum 3, maximum 25 karakter girilmelidir.")])
    username = StringField(label="",validators=[validators.length(max=35,min=5, message="Minimum 5, maximum 35 karakter girilmelidir.")])
    email = StringField(label="",validators=[validators.Email(message="Geçerli email adresi girilmedi !")])
    password = PasswordField(label="",validators=[
        validators.DataRequired(message="Parola oluşturulmadı !"),
        validators.EqualTo(fieldname="confirm",message="Parololar aynı değildir !"),
        validators.length(min=8, message="Parola minimum 8 karakter girilmelidir.")
    ])
    confirm = PasswordField(label="")

# Kullanıcı giriş formu oluşturuluyor
class loginForm(Form):
    username = StringField(label="")
    password = PasswordField(label="")

# makale formu oluşturuluyor
class articleForm(Form):
    title = StringField(label="",validators = [validators.length(max=100,min=10,message="Min. 10, Max. 100 karakter olmalıdır.!")])
    content = TextAreaField(label="",validators = [validators.length(min=10,message="Min. 10 karakter girilmelidir.")])


@app.route("/")
@login_required #eğer giriş yapılmışsa form sayfası gözükecektir.
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/article")
@login_required # eğer kullanıcı grişi varsa makalelerim sayfası gözükecektir.
def article():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)
    
    if result > 0 :
        articles = cursor.fetchall()
        return render_template("article.html", articles = articles, result = result)
    else:
        return render_template("article.html")


@app.route("/dashboard")
@login_required # eğer kullanıcı girişi varsa "bana özel sayfasına giriş yapılacak"
def dashboard():
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE author = %s"
        result = cursor.execute(sorgu,(session["username"],))

        if result > 0 :
            specialArticles = cursor.fetchall()
            return render_template("dashboard.html",specialArticles = specialArticles)
        else:
            return render_template("dashboard.html")

@app.route("/details/<string:id>")
@login_required
def detailArticle(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(sorgu,(id,))
    
    if result > 0:
        art = cursor.fetchone()
        return render_template("details.html", art = art)
    else:
        return render_template("details.html")



# makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0 :
        sorgu2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Sadece yetkili olduğunuz makaleleri silebilirsiniz.","danger")
        return redirect(url_for("index"))

#makale güncelleme
@app.route("/edit/<string:id>", methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE id = %s AND author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))

        # makalenin olup bize ait olmama durumu yada hiç olmama durumu
        if result == 0:
            flash("Makale erişim yetkiniz bulunmamaktadır.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = articleForm() #form mevcutta olan içeriklerden kullanılacağı için ( Form ) nesnesinden türetilmedi.
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form)

    #POTS Durumu
    else:
        form = articleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        result = cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        
        flash("Güncelleme başarıyla gerçekleşti.","succes")
        return redirect(url_for("dashboard"))

# makale arama fonksiyonu
@app.route("/search",methods = ["GET","POST"]) 
def search():
    if request.method == "GET":
        return redirect(url_for("index"))   
    else:
        # article.html sayfasında oluşturulan form dki name değeri alınıyor
        keyword = request.form.get("searchWord")
        
        cursor = mysql.connection.cursor()
        # searchox içerisine yazılan değer burada alınıyor ve database de aratılıyor.
        sorgu = "SELECT * FROM articles WHERE title  LIKE '%"+ keyword + "%' "
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Makale Bulunamadı.!","warning")
            return redirect(url_for("article"))
        else:
            articles = cursor.fetchall()
            return render_template("article.html", articles = articles)




@app.route("/addArticle", methods = ["GET","POST"])
@login_required
def addarticle():
    form = articleForm(request.form)
    if request.method == "POST" and form.validate():
        tile = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(tile,session["username"],content))
        mysql.connection.commit()
        cursor.close() #veritabanı bağlantısı kesiliyor.
        flash("Makale başarıyla eklenmiştir.!","success")
        return redirect(url_for("dashboard"))

    return render_template("addArticle.html",form = form)

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login")) # htm sayfası çağırılmadan direk login sayfasına gidiyor.
    # eğer html göstermek isteseydik "return render_template("login.html") olacaktı."

@app.route("/login",methods = ["GET","POST"]) # url GET de olabilir POST da
def login():
    form = loginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        passwordEntered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(sorgu,(username,))

        if result > 0 :
            data = cursor.fetchone() # kullanıcın bilgileri veri tabanından alınıyor.
            realPasswrod = data["password"]
            if passwordEntered == realPasswrod:

                # kullanıcının giriş durumunu kontrol etmek için
                session["login"] = True
                session["username"] = username
                
                return redirect(url_for("index"))
            else:
                flash("Parola yanlış.!","danger")
                return redirect(url_for("login"))
        else:
            flash("Kullanıcı bulunamadı. !","danger")
            return redirect(url_for("login"))
    

    return render_template("login.html",form = form)

@app.route("/register",methods = ["GET","POST"]) # url GET de olabilir POST da
def register():
    

    form = registerForm(request.form) # forma istek gönderiiyor

    if request.method == "POST" and form.validate(): # eğer sayfaya bir form (post) gönderildiyse ve formda hata yoksa
        # veritabanına veri ekleniyor.
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = form.password.data
        confirm = sha256_crypt.encrypt(form.confirm.data)
        
        cursor = mysql.connection.cursor()

        sorgu = "INSERT INTO users(name,username,email,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,username,email,password))
        mysql.connection.commit()
        cursor.close()

        # flash mesajı oluşturuluyor. kayıt başarılı ise yayınlanacak
        flash("Kayıt işlemi yapılmıştır.!","success")
        
        return redirect(url_for("login")) #fonksiyon ismine göre url ye gönderiliyor. url_for ile dizin belirtiliyor.

    else: # değilse sadece sayfa yapısını göster ve form = form ile form alanlarını sayfaya yazdır.
        return render_template("register.html",form = form)


if __name__ == "__main__":
    app.run(debug=True)

