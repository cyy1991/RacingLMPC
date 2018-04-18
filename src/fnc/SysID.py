def LMPC_EstimateABC(LinPoints, N, n, d, SS, uSS, TimeSS, qp, matrix, PointAndTangent, dt, it):
    import numpy as np
    from SysModel import Curvature
    import datetime

    it = 1
    x = SS[0:TimeSS[it], :, it]
    u = uSS[0:TimeSS[it]-1, :, it]

    Atv = []; Btv = []; Ctv = []; indexUsed_list = []

    for i in range(0, N + 1):
        MaxNumPoint = 500 # Need to reason on how these points are selected
        x0 = LinPoints[i, :]

        Ai = np.zeros((n, n))
        Bi = np.zeros((n, d))
        Ci = np.zeros((n, 1))

        # Compute Index to use
        h = 2
        lamb = 0.0
        stateFeatures = [0, 1, 2]
        scaling = np.eye(len(stateFeatures))

        indexSelected, K = ComputeIndex(h, x, x0, stateFeatures, scaling, MaxNumPoint)
        # =========================
        # ====== Identify vx ======
        inputFeatures = [1]
        Q, M= Compute_Q_M(SS, uSS, indexSelected, stateFeatures, inputFeatures, it, np, matrix, lamb, K)

        yIndex = 0
        AA, BB, CC = LMPC_LocLinReg(Q, K, stateFeatures, inputFeatures, qp, SS, yIndex, it, matrix, M, indexSelected)

        Ai[yIndex, stateFeatures], Bi[yIndex, inputFeatures], Ci[yIndex], indexUsed = LocLinReg(h, x, u, x0, yIndex, stateFeatures, inputFeatures, scaling, qp, matrix, lamb, MaxNumPoint)
        if (indexSelected==indexUsed).all() and (AA==Ai[yIndex, stateFeatures]).all() and (BB==Bi[yIndex, inputFeatures]).all() and (CC==Ci[yIndex]).all():
            print "True"
        else:
            print "Error!!!!!"
        # =========================
        # ====== Identify vy ======
        stateFeatures = [0, 1, 2]
        inputFeatures = [0] # May want to add acceleration here
        yIndex = 1
        scaling = np.eye(len(stateFeatures))

        Ai[yIndex, stateFeatures], Bi[yIndex, inputFeatures], Ci[yIndex], indexUsed = LocLinReg(h, x, u, x0, yIndex, stateFeatures, inputFeatures, scaling, qp, matrix, lamb, MaxNumPoint)

        # Ai1[yIndex, stateFeatures] = np.asarray(Res_vy)[i][0]
        # Bi1[yIndex, inputFeatures] = np.asarray(Res_vy)[i][1]
        # Ci1[yIndex] = np.asarray(Res_vy)[i][2]
        # =========================
        # ====== Identify wz ======
        stateFeatures = [0, 1, 2]
        inputFeatures = [0] # May want to add acceleration here
        yIndex = 2
        scaling = np.eye(len(stateFeatures))

        Ai[yIndex, stateFeatures], Bi[yIndex, inputFeatures], Ci[yIndex], indexUsed = LocLinReg(h, x, u, x0, yIndex, stateFeatures, inputFeatures, scaling, qp, matrix, lamb, MaxNumPoint)

        # Ai1[yIndex, stateFeatures] = np.asarray(Res_wz)[i][0]
        # Bi1[yIndex, inputFeatures] = np.asarray(Res_wz)[i][1]
        # Ci1[yIndex] = np.asarray(Res_wz)[i][2]
        # ===========================
        # ===== Linearization =======
        vx = x0[0]; vy   = x0[1]
        wz = x0[2]; epsi = x0[3]
        s  = x0[4]; ey   = x0[5]

        if s<0:
            print "s is negative, here the state: \n", LinPoints

        startTimer = datetime.datetime.now()  # Start timer for LMPC iteration
        cur = Curvature(s, PointAndTangent)
        den = 1 - cur *ey
        # ===========================
        # ===== Linearize epsi ======
        # epsi_{k+1} = epsi + dt * ( wz - (vx * np.cos(epsi) - vy * np.sin(epsi)) / (1 - cur * ey) * cur )
        depsi_vx   =     -dt * np.cos(epsi) / den * cur
        depsi_vy   =      dt * np.sin(epsi) / den * cur
        depsi_wz   =      dt
        depsi_epsi =  1 - dt * ( -vx * np.sin(epsi) - vy * np.cos(epsi) ) / den * cur
        depsi_s    =      0                                                                      # Because cur = constant
        depsi_ey   =    - dt * (vx * np.cos(epsi) - vy * np.sin(epsi)) / (den**2) * cur * (-cur)

        Ai[3, :]   = [depsi_vx, depsi_vy, depsi_wz, depsi_epsi, depsi_s, depsi_ey]

        # ===========================
        # ===== Linearize s =========
        # s_{k+1} = s    + dt * ( (vx * np.cos(epsi) - vy * np.sin(epsi)) / (1 - cur * ey) )
        ds_vx    =  dt * (np.cos(epsi) / den)
        ds_vy    = -dt * (np.sin(epsi) / den)
        ds_wz    =  0
        ds_epsi  =  dt * (-vx * np.sin(epsi) - vy * np.cos(epsi)) / den
        ds_s     = 1 #+ Ts * (Vx * cos(epsi) - Vy * sin(epsi)) / (1 - ey * rho) ^ 2 * (-ey * drho);
        ds_ey    =  dt * ( vx * np.cos(epsi) - vy * np.sin(epsi)) / (( den )**2)* (-cur)

        Ai[4, :] = [ds_vx, ds_vy, ds_wz, ds_epsi, ds_s, ds_ey]

        # ===========================
        # ===== Linearize ey ========
        # ey_{k+1} = ey + dt * (vx * np.sin(epsi) + vy * np.cos(epsi))
        dey_vx   = dt * np.sin(epsi)
        dey_vy   = dt * np.cos(epsi)
        dey_wz   = 0
        dey_epsi = dt * ( vx * np.cos(epsi) - vy *np.sin(epsi) )
        dey_s    = 0
        dey_ey   = 1

        Ai[5, :] = [dey_vx, dey_vy, dey_wz, dey_epsi, dey_s, dey_ey]

        endTimer = datetime.datetime.now();    deltaTimer_tv = endTimer - startTimer
        # print "Real Lin Time: ", deltaTimer_tv.total_seconds()

        # Atv1.append(Ai1)
        # Btv1.append(Bi1)
        # Ctv1.append(Ci1)
        Atv.append(Ai)
        Btv.append(Bi)
        Ctv.append(Ci)
        indexUsed_list.append(indexUsed)

    # print "Tot Atv1 ins: ", Atv1
    # print "Tot Atv is: ", Atv
    # print "Tot Btv1 is: ", Btv1
    # print "Tot Btv is: ", Btv
    # print "Tot Ctv1 is: ", Ctv1
    # print "Tot Ctv is: ", Ctv
    return Atv, Btv, Ctv, indexUsed_list

def Compute_Q_M(SS, uSS, indexSelected, stateFeatures, inputFeatures, it, np, matrix, lamb, K):
    X0 = np.hstack((np.squeeze(SS[np.ix_(indexSelected, stateFeatures, [it])]),
                    np.squeeze(uSS[np.ix_(indexSelected, inputFeatures, [it])], axis=2)))
    M = np.hstack((X0, np.ones((X0.shape[0], 1))))
    Q0 = np.dot(np.dot(M.T, np.diag(K)), M)
    Q = matrix(Q0 + lamb * np.eye(Q0.shape[0]))


    return Q, M

def LMPC_LocLinReg(Q, K, stateFeatures, inputFeatures, qp, SS, yIndex, it, matrix, M, indexSelected):
    import numpy as np
    from numpy import linalg as la
    import datetime

    # K = np.ones(len(index))


    # print "Removable time: ", deltaTimer_tv.total_seconds()
    y = np.squeeze(SS[np.ix_(indexSelected + 1, [yIndex], [it])])
    b = matrix(-np.dot(np.dot(M.T, np.diag(K)), y))

    startTimer = datetime.datetime.now()  # Start timer for LMPC iteration
    res_cons = qp(Q, b) # This is ordered as [A B C]

    endTimer = datetime.datetime.now(); deltaTimer_tv = endTimer - startTimer

    # print "Non removable time: ", deltaTimer_tv.total_seconds()
    Result = np.squeeze(np.array(res_cons['x']))
    A = Result[0:len(stateFeatures)]
    B = Result[len(stateFeatures):(len(stateFeatures)+len(inputFeatures))]
    C = Result[-1]

    return A, B, C

def ComputeIndex(h, x, x0, stateFeatures, scaling, MaxNumPoint):
    import numpy as np
    from numpy import linalg as la
    import datetime

    startTimer = datetime.datetime.now()  # Start timer for LMPC iteration

    # What to learn a model such that: x_{k+1} = A x_k  + B u_k + C
    oneVec = np.ones( (x.shape[0]-1, 1) )
    x0Vec = (np.dot( np.array([x0[stateFeatures]]).T, oneVec.T )).T
    diff  = np.dot(( x[0:-1, stateFeatures] - x0Vec ), scaling)
    # print 'x0Vec \n',x0Vec
    norm = la.norm(diff, 1, axis=1)
    indexTot =  np.squeeze(np.where(norm < h))
    # print indexTot.shape, np.argmin(norm), norm, x0
    if (indexTot.shape[0] >= MaxNumPoint):
        index = np.argsort(norm)[0:MaxNumPoint]
        # MinNorm = np.argmin(norm)
        # if MinNorm+MaxNumPoint >= indexTot.shape[0]:
        #     index = indexTot[indexTot.shape[0]-MaxNumPoint:indexTot.shape[0]]
        # else:
        #     index = indexTot[MinNorm:MinNorm+MaxNumPoint]
    else:
        index = indexTot

    K  = ( 1 - ( norm[index] / h )**2 ) * 3/4
    # K = np.ones(len(index))

    return index, K

def EstimateABC(LinPoints, N, n, d, x, u, qp, matrix, PointAndTangent, dt):
    import numpy as np
    from SysModel import Curvature


    Atv = []; Btv = []; Ctv = []

    for i in range(0, N + 1):
        MaxNumPoint = 500 # Need to reason on how these points are selected
        x0 = LinPoints[i, :]


        Ai = np.zeros((n, n))
        Bi = np.zeros((n, d))
        Ci = np.zeros((n, 1))

        # =========================
        # ====== Identify vx ======
        h = 2
        stateFeatures = [0, 1, 2]
        inputFeatures = [1]
        lamb = 0.0
        yIndex = 0
        scaling = np.array([[1.0, 0.0, 0.0],
                            [0.0, 1.0, 0.0],
                            [0.0, 0.0, 1.0]])

        Ai[yIndex, stateFeatures], Bi[yIndex, inputFeatures], Ci[yIndex], _ = LocLinReg(h, x, u, x0, yIndex, stateFeatures,
                                                                             inputFeatures, scaling, qp, matrix, lamb, MaxNumPoint)

        # =========================
        # ====== Identify vy ======
        h = 2
        stateFeatures = [0, 1, 2]
        inputFeatures = [0] # May want to add acceleration here
        lamb = 0.0
        yIndex = 1
        # scaling = np.array([[1.0, 0.0, 0.0],
        #                     [0.0, 1.0, 0.0],
        #                     [0.0, 0.0, 1.0]])
        scaling = np.eye(len(stateFeatures))

        Ai[yIndex, stateFeatures], Bi[yIndex, inputFeatures], Ci[yIndex], _ = LocLinReg(h, x, u, x0, yIndex, stateFeatures,
                                                                             inputFeatures, scaling, qp, matrix, lamb, MaxNumPoint)

        # =========================
        # ====== Identify wz ======
        h = 2
        stateFeatures = [0, 1, 2]
        inputFeatures = [0] # May want to add acceleration here
        lamb = 0.0
        yIndex = 2
        # scaling = np.array([[1.0, 0.0, 0.0],
        #                     [0.0, 1.0, 0.0],
        #                     [0.0, 0.0, 1.0]])
        scaling = np.eye(len(stateFeatures))

        Ai[yIndex, stateFeatures], Bi[yIndex, inputFeatures], Ci[yIndex], _ = LocLinReg(h, x, u, x0, yIndex, stateFeatures,
                                                                             inputFeatures, scaling, qp, matrix, lamb, MaxNumPoint)

        # ===========================
        # ===== Linearization =======
        vx = x0[0]; vy   = x0[1]
        wz = x0[2]; epsi = x0[3]
        s  = x0[4]; ey   = x0[5]

        if s<0:
            print "s is negative, here the state: \n", LinPoints

        cur = Curvature(s, PointAndTangent)
        den = 1 - cur *ey
        # ===========================
        # ===== Linearize epsi ======
        # epsi_{k+1} = epsi + dt * ( wz - (vx * np.cos(epsi) - vy * np.sin(epsi)) / (1 - cur * ey) * cur )
        depsi_vx   =     -dt * np.cos(epsi) / den * cur
        depsi_vy   =      dt * np.sin(epsi) / den * cur
        depsi_wz   =      dt
        depsi_epsi =  1 - dt * ( -vx * np.sin(epsi) - vy * np.cos(epsi) ) / den * cur
        depsi_s    =      0                                                                      # Because cur = constant
        depsi_ey   =    - dt * (vx * np.cos(epsi) - vy * np.sin(epsi)) / (den**2) * cur * (-cur)

        Ai[3, :]   = [depsi_vx, depsi_vy, depsi_wz, depsi_epsi, depsi_s, depsi_ey]

        # ===========================
        # ===== Linearize s =========
        # s_{k+1} = s    + dt * ( (vx * np.cos(epsi) - vy * np.sin(epsi)) / (1 - cur * ey) )
        ds_vx    =  dt * (np.cos(epsi) / den)
        ds_vy    = -dt * (np.sin(epsi) / den)
        ds_wz    =  0
        ds_epsi  =  dt * (-vx * np.sin(epsi) - vy * np.cos(epsi)) / den
        ds_s     = 1 #+ Ts * (Vx * cos(epsi) - Vy * sin(epsi)) / (1 - ey * rho) ^ 2 * (-ey * drho);
        ds_ey    =  dt * ( vx * np.cos(epsi) - vy * np.sin(epsi)) / (( den )**2)* (-cur)

        Ai[4, :] = [ds_vx, ds_vy, ds_wz, ds_epsi, ds_s, ds_ey]

        # ===========================
        # ===== Linearize ey ========
        # ey_{k+1} = ey + dt * (vx * np.sin(epsi) + vy * np.cos(epsi))
        dey_vx   = dt * np.sin(epsi)
        dey_vy   = dt * np.cos(epsi)
        dey_wz   = 0
        dey_epsi = dt * ( vx * np.cos(epsi) - vy *np.sin(epsi) )
        dey_s    = 0
        dey_ey   = 1

        Ai[5, :] = [dey_vx, dey_vy, dey_wz, dey_epsi, dey_s, dey_ey]

        Atv.append(Ai)
        Btv.append(Bi)
        Ctv.append(Ci)

    return Atv, Btv, Ctv

def LocLinReg(h, x, u, x0, yIndex, stateFeatures, inputFeatures, scaling, qp, matrix, lamb, MaxNumPoint):
    import numpy as np
    from numpy import linalg as la
    # What to learn a model such that: x_{k+1} = A x_k  + B u_k + C
    oneVec = np.ones( (x.shape[0]-1, 1) )
    x0Vec = (np.dot( np.array([x0[stateFeatures]]).T, oneVec.T )).T
    diff  = np.dot(( x[0:-1, stateFeatures] - x0Vec ), scaling)
    # print 'x0Vec \n',x0Vec
    norm = la.norm(diff, 1, axis=1)
    indexTot =  np.squeeze(np.where(norm < h))
    if (indexTot.shape[0] >= MaxNumPoint):
        index = np.argsort(norm)[0:MaxNumPoint]
        # MinNorm = np.argmin(norm)
        # if MinNorm+MaxNumPoint >= indexTot.shape[0]:
        #     index = indexTot[indexTot.shape[0]-MaxNumPoint:indexTot.shape[0]]
        # else:
        #     index = indexTot[MinNorm:MinNorm+MaxNumPoint]
    else:
        index = indexTot

    K  = ( 1 - ( norm[index] / h )**2 ) * 3/4
    # K = np.ones(len(index))
    X0 = np.hstack( ( x[np.ix_(index, stateFeatures)], u[np.ix_(index, inputFeatures)] ) )
    M = np.hstack( ( X0, np.ones((X0.shape[0],1)) ) )

    y = x[np.ix_(index+1, [yIndex])]
    b = matrix( -np.dot( np.dot(M.T, np.diag(K)), y) )

    Q0 = np.dot( np.dot(M.T, np.diag(K)), M )
    Q  = matrix( Q0 + lamb * np.eye(Q0.shape[0]) )

    res_cons = qp(Q, b) # This is ordered as [A B C]
    Result = np.squeeze(np.array(res_cons['x']))
    A = Result[0:len(stateFeatures)]
    B = Result[len(stateFeatures):(len(stateFeatures)+len(inputFeatures))]
    C = Result[-1]

    return A, B, C, index


def Regression(x, u, lamb):
    import numpy as np
    # Want to solve W^* = argmin sum_i ||W^T z_i - y_i ||_2^2 + lamb ||W||_F,
    # with z_i = [x_i u_i] and W \in R^{n + d} x n
    Y = x[2:x.shape[0], :]
    X = np.hstack( (x[1:(x.shape[0]-1), :], u[1:(x.shape[0]-1), :]))

    Q = np.linalg.inv( np.dot( X.T, X) + lamb * np.eye( X.shape[1] ) )
    b = np.dot(X.T, Y)
    W = np.dot( Q , b)

    A = W.T[:, 0:6]
    B = W.T[:, 6:8]

    return A, B