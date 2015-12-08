from django.core.urlresolvers import reverse
from django.contrib import messages
from django.forms import ModelForm
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView

from judge.models import TestGroup, Problem

class TestGroupForm(ModelForm):
    class Meta:
        model = TestGroup
        exclude = ['problem']

class TestGroupEdit(View):
    temlpate_name = 'judge/test_group_edit.html'
    title = 'Edit Test group'
    redir_pattern = 'judge:test_group_list'

    def get_context(self, **kwargs):
        context = {'title': self.title }

        if 'pk' in kwargs:
            context['test_group'] = get_object_or_404(TestGroup, pk = kwargs['pk'])
            context['problem_pk'] = context['test_group'].problem.pk
        else:
            context['problem_pk'] = kwargs['problem_id']

        if 'form' in kwargs:
            context['form'] = kwargs['form']
        elif 'test_group' in context:
            context['form'] = TestGroupForm(instance = context['test_group'])
        else:
            context['form'] = TestGroupForm()

        return context

    def get(self, request, **kwargs):
        return render(request, self.temlpate_name, self.get_context(**kwargs))

    def post(self, request, pk):
        testGroup = get_object_or_404(TestGroup, pk = pk)
        form = TestGroupForm(request.POST, instance = testGroup)

        if form.is_valid():
            testGroup = form.save()
            return redirect(self.redir_pattern, problem_id = testGroup.problem.pk)
        else:
            context = self.get_context(form = form, pk = pk)
            return render(request, self.template_name, context)

class TestGroupNew(TestGroupEdit):
    title = 'New Test group'

    def post(self, request, problem_id):
        form = TestGroupForm(request.POST)

        if form.is_valid():
            testGroup = form.save(commit = False)
            testGroup.problem = get_object_or_404(Problem, pk = problem_id)
            testGroup.save()
            
            return redirect(self.redir_pattern, problem_id = problem_id)
        else:
            context = self.get_context(form = form, problem_id = problem_id)
            return render(request, self.template_name, context)

class TestGroupDelete(View):
    template_name = 'judge/test_group_delete.html'

    def get(self, request, pk):
        testGroup = get_object_or_404(TestGroup, pk = pk)
        context = {
            'test_group': testGroup,
            'problem_pk': testGroup.problem.pk
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        testGroup = get_object_or_404(TestGroup, pk = pk)
        testGroup.delete()

        messages.success(request, 'Test group deleted successfully')
        return redirect('judge:test_list', problem_id = testGroup.problem.pk)

class TestGroupList(TemplateView):
    template_name = 'judge/test_group_list.html'

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)

        problem = get_object_or_404(Problem, pk = kwargs['problem_id'])
        context['problem_pk'] = problem.pk
        context['test_groups'] = problem.testgroup_set.all()
        return context
