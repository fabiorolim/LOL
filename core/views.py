import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404

from .forms import SimuladorForm, CategoriaForm, MovimentacaoForm

from .simulador_financeiro import Sac, Price

from .models import Movimentacao, Categoria, ValorOrcamentario


@login_required(login_url='login')
def dashboard(request):
    usuario_logado = get_object_or_404(User, pk=request.user.id)

    total_receber = Movimentacao.objects.filter(usuario=usuario_logado).filter(
        tipo='R').aggregate(
        Sum('valor'))

    total_pagar = Movimentacao.objects.filter(usuario=usuario_logado).filter(
        tipo='P').aggregate(
        Sum('valor'))

    valores_orcamentos = ValorOrcamentario.objects.values(
        'categoria__descricao', 'valor_total', 'valor_disponivel').filter(
        categoria__tipo='P')

    valor_total_receber = 0
    if total_receber['valor__sum'] != None:
        valor_total_receber = total_receber['valor__sum']

    valor_total_pagar = 0
    if total_pagar['valor__sum'] != None:
        valor_total_pagar = total_pagar['valor__sum']

    saldo = valor_total_receber - valor_total_pagar

    # Query gráfico área

    valores_categorias = Movimentacao.objects.values(
        'categoria__descricao').annotate(
        Sum('valor')).filter(usuario=usuario_logado).filter(tipo='P').order_by(
        'valor__sum')

    categorias = []
    for vc in valores_categorias:
        categorias.append(vc['categoria__descricao'])

    valores_c = []
    for vc in valores_categorias:
        valores_c.append(float(vc['valor__sum']))

    # Query gráfico linha

    valores_mes = Movimentacao.objects.values('data__month').annotate(
        Sum('valor')).filter(usuario=usuario_logado).filter(tipo='P').order_by(
        'data__month')

    meses = []
    for vm in valores_mes:
        meses.append(vm['data__month'])

    valores_m = []
    for vm in valores_mes:
        valores_m.append(float(vm['valor__sum']))

    context = {
        'total_pagar': valor_total_pagar,
        'total_receber': valor_total_receber,
        'saldo': saldo,
        'categorias': json.dumps(categorias),
        'valores_categorias': json.dumps(valores_c),
        'qtd_categorias': json.dumps(len(categorias)),
        'meses': json.dumps(meses),
        'valores_meses': json.dumps(valores_m),
        'valores_orcamento': valores_orcamentos,
    }

    return render(request, 'core/index.html', context)


@login_required(login_url='login')
def movimentacao(request):
    if request.method == 'GET':
        form = MovimentacaoForm()
        contexto = {'form': form}

        return render(request, 'core/nova_movimentacao.html', contexto)
    else:
        usuario_logado = get_object_or_404(User, pk=request.user.id)
        form = MovimentacaoForm(data=request.POST)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.usuario = usuario_logado
            conta.save()

            return redirect('movimentacoes')


@login_required(login_url='login')
def movimentacoes(request):
    movimentacoes = Movimentacao.objects.filter(usuario=1).order_by(
        'data_add').reverse()
    context = {
        'movimentacoes': movimentacoes
    }
    return render(request, 'core/movimentacoes.html', context)


@login_required(login_url='login')
def editar_movimentacao(request, id):
    movimentacao = Movimentacao.objects.get(id=id)

    if request.method == 'GET':
        form = MovimentacaoForm(instance=movimentacao)
        contexto = {'form': form, 'conta': movimentacao}
        return render(request, 'core/editar_movimentacao.html', contexto)

    else:
        form = MovimentacaoForm(instance=movimentacao, data=request.POST)
        if form.is_valid():
            form.save()

            return redirect('movimentacoes')


@login_required(login_url='login')
def deletar_movimentacao(request, id):
    conta = Movimentacao.objects.get(id=id)
    conta.delete()
    return redirect('movimentacoes')


@login_required(login_url='login')
def categoria(request):
    if request.method == 'POST':
        usuario_logado = get_object_or_404(User, pk=request.user.id)
        form = CategoriaForm(request.POST)

        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.usuario = usuario_logado
            categoria.save()

            return redirect('categorias')

    else:
        form = CategoriaForm()
        contexto = {'form': form}

        return render(request, 'core/nova_categoria.html', contexto)


@login_required(login_url='login')
def categorias(request):
    categorias = Categoria.objects.filter(usuario=request.user.id)

    context = {
        'categorias': categorias,
    }

    return render(request, 'core/categorias.html', context)


@login_required(login_url='login')
def editar_categoria(request, id):
    categoria = Categoria.objects.get(id=id)

    if request.method == 'GET':
        form = CategoriaForm(instance=categoria)
        contexto = {'form': form, 'categoria': categoria}

        return render(request, 'core/editar_categoria.html', contexto)

    else:
        form = CategoriaForm(instance=categoria, data=request.POST)
        if form.is_valid():
            form.save()

        return redirect('categorias')


@login_required(login_url='login')
def deletar_categoria(request, id):
    categoria = Categoria.objects.get(id=id)
    categoria.delete()
    return redirect('categorias')


@login_required(login_url='login')
def simulador(request):
    if request.method == 'GET':
        form = SimuladorForm()

        return render(request, 'core/nova_simulacao.html',
                      {'form': form})

    else:
        form = SimuladorForm(data=request.POST)
        if form.is_valid():
            if form['tipo'].value() == 'S':
                sac = Sac(float(form['valor'].value()),
                          float(form['taxa'].value()),
                          int(form['prazo'].value()),
                          float(form['entrada'].value()))
                sac.generate_lists()
                context = {
                    'total': sac.total,
                    'entrada': sac.entry,
                    'prazo': sac.n,
                    'taxa': sac.i * 100,
                    'saldo_devedor_inicial': sac.total - sac.entry,
                    'custo_efetivo': sac.efective_cost_total(),
                    'table': sac.generate_table()
                }

            elif form['tipo'].value() == 'P':
                price = Price(float(form['valor'].value()),
                              float(form['taxa'].value()),
                              int(form['prazo'].value()),
                              float(form['entrada'].value()))
                price.generate_lists()
                context = {
                    'total': price.total,
                    'entrada': price.entry,
                    'prazo': price.n,
                    'taxa': price.i * 100,
                    'saldo_devedor_inicial': price.total - price.entry,
                    'custo_efetivo': price.efective_cost_total(),
                    'table': price.generate_table()
                }

            return render(request, 'core/tabela_simulacao.html',
                          context)
