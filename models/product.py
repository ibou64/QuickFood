from extensions import db


class Product(db.Model):
    __tablename__ = "product"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    price       = db.Column(db.Float, nullable=False)
    stock       = db.Column(db.Integer, default=0)
    image       = db.Column(db.String(200), default="")

    # Vidéo : fichier uploadé OU lien externe (YouTube / TikTok)
    video_file  = db.Column(db.String(200), nullable=True)   # nom fichier local
    video_url   = db.Column(db.String(500), nullable=True)   # lien YouTube/TikTok

    restaurant_id = db.Column(
        db.Integer, db.ForeignKey("restaurant.id"), nullable=False
    )

    # Relations
    restaurant = db.relationship("Restaurant", back_populates="products")

    @property
    def has_video(self):
        return bool(self.video_file or self.video_url)

    @property
    def video_embed_url(self):
        """Retourne l'URL embed pour YouTube/TikTok."""
        if not self.video_url:
            return None
        url = self.video_url.strip()
        # YouTube
        import re
        yt = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})', url)
        if yt:
            return f"https://www.youtube.com/embed/{yt.group(1)}?rel=0&modestbranding=1"
        # TikTok
        tt = re.search(r'tiktok\.com/.+/video/(\d+)', url)
        if tt:
            return f"https://www.tiktok.com/embed/v2/{tt.group(1)}"
        # Lien direct autre
        return url

    def __repr__(self):
        return f"<Product {self.name} - {self.price} FCFA>"
