from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .ownership import company_required


@login_required
@company_required
def performance(request,workspace_id):
    posts=list(request.workspace.own_posts.select_related("run").prefetch_related("snapshots").order_by("-published_at")[:100])
    for post in posts:
        post.latest=max(post.snapshots.all(),key=lambda s:(s.observed_at,s.pk),default=None)
    return render(request,"engine/own_performance.html",{"workspace":request.workspace,"own_posts":posts,"channel":"own"})
