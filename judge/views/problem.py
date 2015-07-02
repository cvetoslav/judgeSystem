from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.urlresolvers import reverse
from django.db.transaction import set_autocommit, commit
from django.forms import ModelForm, Form, IntegerField, DecimalField
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, DetailView, View

from judge.models import Problem, Test, Solution, UserProblemData
from judge.tasks import test_solution

class ProblemForm(ModelForm):
    class Meta:
        model = Problem
        exclude = ['maxScore']

class ProblemList(TemplateView):
    template_name = 'judge/problem_list.html'

    def get_context_data(self, page = 1):
        paginator = Paginator(Problem.objects.all(), 5)
        context = super(ProblemList, self).get_context_data()

        if int(page) < 1:
            page = 1

        try:
            page = paginator.page(page)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)
        
        user = self.request.user
        if user.is_authenticated():
            for prob in page.object_list :
                
                try :
                    solData = UserProblemData.objects.get(problem = prob, 
                                                        user = user)
                
                    if solData.maxScore == prob.maxScore:
                        prob.status = 'solved'
                    else:
                        prob.status = 'attempted'

                except UserProblemData.DoesNotExist :
                    prob.status = 'not_attempted'

        context['page'] = page
    
        return context

class ProblemDetails(View):
    model = Problem
    context_object_name = 'problem'
    template_name = 'judge/problem_details.html'

    def get(self, request, pk):
        problem = get_object_or_404(Problem, pk = pk)
        solutions = []
        
        if request.user.is_authenticated():
            solutions = Solution.objects.filter(user = request.user,
                    problem = problem)[:20]

        context = {'problem': problem, 'solutions': solutions}
        return render(request, self.template_name, context)

class ProblemNew(View):
    template_name = 'judge/problem_edit.html'
    title = 'Add a problem'

    def get_context(self, form):
        return {
            'form' : form,
            'title' : self.title
        }

    def get(self, request):
        context = self.get_context(ProblemForm())
        return render(request, self.template_name, context)

    def post(self, request):
        form = ProblemForm(request.POST)

        if not form.is_valid():
            context = self.get_context(form)
            return render(request, self.template_name, context)

        problem = form.save()
        url = reverse('judge:problem_details', args = (problem.pk,))
        return HttpResponseRedirect(url)

class ProblemEdit(View):
    template_name = 'judge/problem_edit.html'
    title = 'Edit statement'

    def get_context(self, problem, form):
        pk = problem.pk
        return {
            'form' : form,
            'title': self.title,
            'tests': problem.test_set,
            'problem_pk'   : pk
        }

    def get(self, request, pk = 0):
        problem = get_object_or_404(Problem, pk = pk)
        tests = problem.test_set
        form = ProblemForm(instance = problem)

        context = self.get_context(problem, form)
        return render(request, self.template_name, context)

    def post(self, request, pk = 0):
        problem = get_object_or_404(Problem, pk = pk)

        form = ProblemForm(request.POST, instance = problem)

        if not form.is_valid():
            context = self.get_context(problem, form)
            return render(request, self.template_name, context)

        form.save()
        url = reverse('judge:problem_details', args = (pk,))
        return HttpResponseRedirect(url)

class ProblemDelete(View):
    template_name = 'judge/problem_delete.html'

    def get(self, request, pk):
        problem = get_object_or_404(Problem, pk = pk)

        context = {
            'modelName': problem.title,
            'modelType': 'problem',
            'cancelUrl': reverse('judge:problem_edit', args = (pk,)),
            'problem_pk': pk
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        curProblem = Problem.objects.get(pk = pk)
        curProblem.delete()

        messageText = 'You\'ve Successfuly deleted this problem'
        messages.add_message(request, messages.SUCCESS, messageText)
        
        url = reverse('judge:problem_list')
        return HttpResponseRedirect(url)

class ProblemGlobalForm(Form):
    timeLimit = DecimalField(required = False, decimal_places = 4)
    memoryLimit = IntegerField(required = False)
    pointsPerTest = IntegerField(required = False)

class ProblemGlobal(View):
    template_name = 'judge/problem_global.html'

    def get_context(self, form, pk):
        return {
            'form': form,
            'problem_pk': pk
        }

    def get(self, request, pk):
        form = ProblemGlobalForm()
        context = self.get_context(form, pk)
        return render(request, self.template_name, context)
        
    def post(self, request, pk):
        form = ProblemGlobalForm(request.POST)

        if not form.is_valid():
            context = self.get_context(form, pk)
            return render(request, self.template_name, context)

        problem = get_object_or_404(Problem, pk = pk)

        timeLimit = form.cleaned_data['timeLimit']
        memoryLimit = form.cleaned_data['memoryLimit']
        pointsPerTest = form.cleaned_data['pointsPerTest']

        for test in problem.test_set.all():
            if not timeLimit == None:
                test.time_limit = timeLimit
            if not memoryLimit == None:
                test.mem_limit = memoryLimit
            if not pointsPerTest == None:
                test.points = pointsPerTest

            test.save()
        
        messageText = 'Test updated successfully'
        messages.add_message(request, messages.SUCCESS, messageText)

        url = reverse('judge:problem_edit', args=(pk,))
        return HttpResponseRedirect(url)

class ProblemRetest(View):
    template_name = 'judge/problem_retest.html'

    def get(self, request, pk):
        problem = get_object_or_404(Problem, pk = pk)
        solCnt = Solution.objects.filter(problem = problem).count()

        context = {
            'problem_pk': pk,
            'solutionCount': solCnt
        }

        return render(request, self.template_name, context)

    def post(self, request, pk):
        problem = get_object_or_404(Problem, pk = pk)
        solutions = problem.solution_set.all()

       # set_autocommit(False)
        for sol in solutions:
            sol.testresult_set.all().delete()
            sol.score = 0
            sol.grader_message = 'retesting'
            sol.save()

            test_solution.delay(sol)

        #commit()
        #set_autocommit(True)

        messageText = "Solutions added to the queue."
        messages.add_message(request, messages.SUCCESS, messageText)

        url = reverse('judge:problem_edit', args=(pk,))
        return HttpResponseRedirect(url)

        problem = get_object_or_404(Problem, pk = pk)
        return HttpResponse(problem.stdin, content_type="text/plain")
