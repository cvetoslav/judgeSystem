import datetime

from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.forms import Form, CharField, Textarea
from django.shortcuts import render, get_object_or_404
from django.http import Http404, HttpResponseRedirect
from django.views.generic import DetailView, View
from django.utils import timezone

from judge.models import Problem, Solution
from judge.tasks import test_solution

class SolutionDetails(DetailView):
    template_name = 'judge/solution_details.html'
    model = Solution
    context_object_name = 'solution'

class SolutionSubmitForm(Form):
    source = CharField(label = 'Source Code',
                            widget = Textarea())

class SolutionSubmit(View):
    template_name = 'judge/solution_submit.html'
            
    def render(self, request):
        context = {
            'problem': self.problem,
            'form': self.form,}
        return render(request, self.template_name, context)

    def get(self, request, pk):
        self.form = SolutionSubmitForm()
        self.problem = get_object_or_404(Problem, pk = pk)

        if not request.user.is_active:
            return HttpResponseRedirect(reverse('judge:login'))

        return self.render(request)

    def post(self, request, pk):
        self.problem = get_object_or_404(Problem, pk = pk)
        self.form = SolutionSubmitForm(request.POST)
        
        user = request.user
        if not user.is_active:
            return HttpResponseRedirect(reverse('judge:login'))

        if not self.form.is_valid():
            return self.render(request)

        source = self.form.cleaned_data['source']
        solution = Solution(
            source = source,
            submit_date = timezone.now(),
            grader_message = 'In Queue',
            user = user,
            problem = self.problem)

        solution.save()
        
        test_solution.delay(solution)

        url = reverse('judge:solution_details', args = (solution.pk,))
        return HttpResponseRedirect(url)

