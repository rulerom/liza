"""Independent boundary oracle; does not read protocol flags to choose transitions."""
def check(text):
    queue=[]; closed=False; armed=False; pending=False; fault=False; inject=False
    for line_number, line in enumerate(text.splitlines(), 1):
        parts=line.split(); op=parts[0]
        if op=='start':
            queue=[]; closed=False; armed=False; pending=False; fault=False; inject=False
            continue
        if op=='inject':
            inject=True
            continue
        if op=='ready':
            assert parts[1]=='1', (line_number, 'durable notification not readable', line)
            continue
        if op=='fault':
            assert int(parts[1])==fault, (line_number, 'fault observation', line)
            continue
        value,result,reason,a,p,f=map(int,parts[1:])
        def notify():
            nonlocal fault,pending
            if not fault and armed and not pending:
                if inject: fault=True
                else: pending=True
            return not fault
        if op=='publish':
            if fault or closed: expected,why=0,3
            elif len(queue)==2: expected,why=0,1
            else:
                queue.append(value)
                expected,why=(1 if notify() else 2),0
            assert (result,reason)==(expected,why), (line_number,'publication result',line)
        elif op=='take':
            pending=False; armed=False
            if queue:
                expected=0
                assert value==queue.pop(0), (line_number,'FIFO integrity',line)
            else:
                expected=3 if closed else 2
                armed=not closed and not fault
            assert result==expected, (line_number,'receive result',line)
        elif op=='close':
            closed=True
            assert result==notify(), (line_number,'close result',line)
        else: raise AssertionError(('unknown event',line))
        assert (a,p,f)==(armed,pending,fault), (line_number,'boundary state',line,(armed,pending,fault))
